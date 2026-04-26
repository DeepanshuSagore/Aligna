import os
import json
import re
import io
import asyncio
import time
from collections import Counter
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from groq import Groq
from motor.motor_asyncio import AsyncIOMotorClient
import PyPDF2
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.local")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MOCK_CANDIDATES_PATH = os.path.join(PROJECT_ROOT, "mock_candidates.json")

# Gemini model - used for JD parsing (low volume)
GEMINI_MODEL = 'gemini-2.0-flash'

# Groq config - used for simulation (high volume, fast, generous free tier)
DEFAULT_GROQ_MODELS = [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'gemma2-9b-it',
]
GROQ_MODELS = [
    model.strip()
    for model in os.getenv('GROQ_MODELS', ','.join(DEFAULT_GROQ_MODELS)).split(',')
    if model.strip()
]
GROQ_RATE_LIMIT_COOLDOWN_SECONDS = int(os.getenv('GROQ_RATE_LIMIT_COOLDOWN_SECONDS', '90'))
groq_model_cooldown_until: dict[str, float] = {}
groq_rr_index = 0
groq_key = os.getenv("GROQ_API_KEY")
groq_client = None
if groq_key:
    groq_client = Groq(api_key=groq_key)
    print(f"Groq configured with models: {', '.join(GROQ_MODELS)}")
else:
    print("WARNING: GROQ_API_KEY not found. Will fall back to Gemini for simulations.")

def _is_groq_rate_limit_error(error_text: str) -> bool:
    lowered = error_text.lower()
    markers = ('429', 'rate limit', 'too many requests', 'quota', 'resource exhausted')
    return any(marker in lowered for marker in markers)

def _extract_retry_delay_seconds(error_text: str) -> Optional[int]:
    # Example message: "Please retry in 24.9s"
    match = re.search(r'(?:retry|try again)[^0-9]*(\d+(?:\.\d+)?)\s*(?:s|sec|second)', error_text.lower())
    if not match:
        return None
    return max(1, int(float(match.group(1))))

def _strip_code_fences(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

def _clamp_score(value, default: int = 0) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        parsed = default
    return max(0, min(parsed, 100))

def _is_unspecified(value: Optional[str]) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized in {
        "",
        "none",
        "not specified",
        "not mentioned",
        "not provided",
        "not disclosed",
        "n/a",
        "na",
        "unspecified",
        "unknown",
        "unknown role",
        "no preference",
        "no location preference",
        "location not specified",
        "location unspecified",
        "tbd",
        "to be decided",
        "to be determined",
    }

def _normalize_free_text(value: str) -> str:
    return re.sub(r'[^a-z0-9+#.\s]+', ' ', (value or '').lower()).strip()

WORK_MODE_REMOTE_ONLY = "Remote only"
WORK_MODE_ONSITE_ONLY = "On-site only"
WORK_MODE_HYBRID = "Hybrid"
WORK_MODE_FLEXIBLE = "Flexible"
WORK_MODE_NOT_SPECIFIED = "Not specified"

_WORK_MODE_NON_GEO_TOKENS = {
    "remote", "hybrid", "onsite", "on", "site", "office", "in", "only", "global", "worldwide",
    "anywhere", "any", "wfh", "wfo", "work", "from", "home", "mode", "arrangement", "preferred",
    "preference", "location", "loc", "based", "flexible", "either", "no", "none", "not", "specified",
    "unspecified", "provided", "disclosed",
}

_US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}

_LOCATION_ALIAS_GROUPS = [
    {
        "aliases": {"us", "usa", "america", "united states", "united states of america"},
        "tokens": {"us", "usa", "america"},
    },
    {
        "aliases": {"uk", "united kingdom", "great britain", "britain", "england"},
        "tokens": {"uk", "britain", "england"},
    },
    {
        "aliases": {"uae", "united arab emirates"},
        "tokens": {"uae", "emirates"},
    },
]

_LOW_SIGNAL_LOCATION_TOKENS = {
    "united", "states", "kingdom", "arab", "republic", "state", "province",
}

def _normalize_work_location_preference(value: Optional[str]) -> str:
    text = _normalize_free_text(value or "")
    if not text or text in {"na", "n a", "none", "not specified", "unspecified", "unknown"}:
        return WORK_MODE_NOT_SPECIFIED

    text_tokens = set(text.split())
    has_remote = any(token in text for token in ("remote", "wfh", "work from home", "home based"))
    has_hybrid = "hybrid" in text
    has_onsite = any(token in text for token in ("onsite", "on site", "in office", "office", "wfo", "offline"))
    has_flexible = (
        "any" in text_tokens
        or "flexible" in text_tokens
        or "either" in text_tokens
        or "anywhere" in text_tokens
        or "location flexible" in text
    )
    has_remote_only_signal = any(token in text for token in ("remote only", "fully remote", "100 remote", "exclusive remote"))

    if has_hybrid:
        return WORK_MODE_HYBRID
    if has_flexible and not (has_remote or has_onsite):
        return WORK_MODE_FLEXIBLE
    if has_onsite and has_remote:
        return WORK_MODE_HYBRID
    if has_onsite:
        return WORK_MODE_ONSITE_ONLY
    if has_remote or has_remote_only_signal:
        return WORK_MODE_REMOTE_ONLY
    if has_flexible:
        return WORK_MODE_FLEXIBLE

    return WORK_MODE_NOT_SPECIFIED

def _extract_geographic_tokens(location_text: str) -> List[str]:
    if _is_unspecified(location_text):
        return []

    normalized = _normalize_free_text(location_text)
    if not normalized:
        return []
    base_tokens = {
        token for token in normalized.split()
        if token and token not in _WORK_MODE_NON_GEO_TOKENS
    }
    normalized_tokens = set(normalized.split())

    for group in _LOCATION_ALIAS_GROUPS:
        aliases = group["aliases"]
        alias_matched = False
        for alias in aliases:
            alias = alias.strip().lower()
            if not alias:
                continue
            if " " in alias:
                if alias in normalized:
                    alias_matched = True
                    break
            else:
                if alias in normalized_tokens:
                    alias_matched = True
                    break

        if alias_matched:
            base_tokens.update(group["tokens"])

    # If city has a US state code suffix (e.g. "Seattle, WA"), infer US geography.
    location_parts = [part.strip().upper() for part in re.split(r"[,()]", location_text or "") if part.strip()]
    if any(part in _US_STATE_CODES for part in location_parts):
        for group in _LOCATION_ALIAS_GROUPS:
            if "usa" in group["tokens"]:
                base_tokens.update(group["tokens"])
                break

    return sorted(token for token in base_tokens if token not in _LOW_SIGNAL_LOCATION_TOKENS)

def _has_geographic_location_hint(location_text: str) -> bool:
    return len(_extract_geographic_tokens(location_text)) > 0

def _normalize_candidate_doc(doc: dict) -> dict:
    normalized = dict(doc)
    raw_id = normalized.pop("_id", None)
    existing_id = normalized.get("id")
    normalized["id"] = str(existing_id or raw_id or "")

    # Ensure stable defaults so API responses are always shape-safe for the UI.
    normalized.setdefault("name", "Unknown Candidate")
    normalized.setdefault("role", "Unknown Role")
    normalized.setdefault("city", "Unknown City")
    normalized.setdefault("remote_preference", "Not specified")
    normalized.setdefault("expected_salary", "Not specified")
    normalized.setdefault("education", "Not specified")
    normalized.setdefault("last_company", "Not specified")
    normalized.setdefault("open_to_work", False)

    skills = normalized.get("skills", [])
    if not isinstance(skills, list):
        skills = []
    normalized["skills"] = [str(skill) for skill in skills if skill is not None]

    try:
        normalized["years_experience"] = int(float(normalized.get("years_experience", 0)))
    except (TypeError, ValueError):
        normalized["years_experience"] = 0

    normalized_pref = _normalize_work_location_preference(str(normalized.get("remote_preference", "")))
    normalized["remote_preference"] = normalized_pref
    normalized["work_location_preference"] = normalized_pref

    normalized["match_score"] = _clamp_score(normalized.get("match_score", 0))
    normalized["match_reason"] = str(normalized.get("match_reason", "") or "")
    return normalized

def _load_candidates_from_mock(limit: Optional[int] = None) -> List[dict]:
    with open(MOCK_CANDIDATES_PATH, "r") as f:
        data = json.load(f)
    normalized = [_normalize_candidate_doc(candidate) for candidate in data]
    if limit is None:
        return normalized
    return normalized[:max(0, limit)]

async def _load_candidates(limit: Optional[int] = None) -> tuple[List[dict], str]:
    global db

    if db is not None:
        try:
            cursor = db.candidates.find({})
            if limit is not None:
                cursor = cursor.limit(max(0, limit))

            candidates_data: List[dict] = []
            async for doc in cursor:
                candidates_data.append(_normalize_candidate_doc(doc))

            if candidates_data:
                return candidates_data, "mongodb"
        except Exception as e:
            print(f"MongoDB read error: {e}")
            print("Falling back to local mock candidates for this and future requests.")
            db = None

    return _load_candidates_from_mock(limit=limit), "mock_json"

async def _generate_gemini_text(prompt: str, model_name: str = GEMINI_MODEL) -> str:
    model = genai.GenerativeModel(model_name)
    response = await asyncio.to_thread(model.generate_content, prompt)
    return ((getattr(response, "text", None) or "").strip())

async def call_groq(prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """Call Groq API with model failover and per-model cooldown."""
    global groq_rr_index
    if not groq_client:
        raise Exception("Groq client not configured")

    if not GROQ_MODELS:
        raise Exception("No Groq models configured")

    now = time.time()
    models_in_order = GROQ_MODELS[groq_rr_index:] + GROQ_MODELS[:groq_rr_index]
    last_error = None

    for model_name in models_in_order:
        cooldown_until = groq_model_cooldown_until.get(model_name, 0)
        if cooldown_until > now:
            continue

        try:
            response = await asyncio.to_thread(
                groq_client.chat.completions.create,
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            # Round-robin on success to spread usage across models.
            groq_rr_index = (GROQ_MODELS.index(model_name) + 1) % len(GROQ_MODELS)
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            error_text = str(e)
            if _is_groq_rate_limit_error(error_text):
                retry_delay = _extract_retry_delay_seconds(error_text) or GROQ_RATE_LIMIT_COOLDOWN_SECONDS
                groq_model_cooldown_until[model_name] = time.time() + retry_delay
                print(f"Groq model {model_name} rate limited. Cooling down for {retry_delay}s.")
            else:
                print(f"Groq model {model_name} failed: {e}")

    if last_error:
        raise Exception(f"All Groq models unavailable. Last error: {last_error}")

    raise Exception("All Groq models are in cooldown. Try again shortly.")

async def call_gemini_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Call Gemini API with retry logic for rate limits."""
    for attempt in range(max_retries):
        try:
            return await _generate_gemini_text(prompt, GEMINI_MODEL)
        except Exception as e:
            error_str = str(e)
            if '429' in error_str and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"Gemini rate limited, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                raise e
    raise Exception("Max retries exceeded")

async def call_groq_then_gemini(prompt: str) -> str:
    """Try Groq first, then Gemini with retry."""
    errors: List[str] = []
    for provider, call_fn in [
        ("Groq", lambda p: call_groq(p, temperature=0.1, max_tokens=900)),
        ("Gemini", call_gemini_with_retry),
    ]:
        try:
            return await call_fn(prompt)
        except Exception as e:
            errors.append(f"{provider}: {e}")

    raise Exception(" | ".join(errors) if errors else "No providers available")

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY not found in environment.")
else:
    genai.configure(api_key=api_key)

# MongoDB Setup
mongo_uri = os.getenv("MONGODB_URI")
db_client = None
db = None
if mongo_uri:
    try:
        db_client = AsyncIOMotorClient(
            mongo_uri,
            serverSelectionTimeoutMS=2500,
            connectTimeoutMS=2500,
            socketTimeoutMS=2500,
            tlsAllowInvalidCertificates=False,
        )
        db = db_client.aligna
        print("MongoDB URI configured. Connection will be validated on first read.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")

app = FastAPI(title="ALIGNA Backend", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobDescriptionRequest(BaseModel):
    job_description: str

class JobDescriptionResponse(BaseModel):
    role: str
    experience_required: str
    must_have_skills: List[str]
    good_to_have_skills: List[str]
    location: str
    work_location_preference: str = WORK_MODE_NOT_SPECIFIED
    seniority: str
    summary: str
    parse_success: bool = True
    warning: Optional[str] = None

KNOWN_SKILL_TERMS = [
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#", "PHP", "Ruby",
    "React", "Next.js", "Angular", "Vue", "Node.js", "Express", "FastAPI", "Django", "Flask",
    "Spring Boot", "GraphQL", "REST", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD", "GitHub Actions",
    "Machine Learning", "Data Science", "PyTorch", "TensorFlow", "NLP", "LLM", "GenAI",
    "UI/UX", "Figma", "Microservices", "System Design", "Testing", "Jest", "Playwright", "Selenium"
]

SENIORITY_TO_EXPERIENCE = {
    "entry": "0-1 years",
    "junior": "1-2 years",
    "mid": "3+ years",
    "senior": "5+ years",
    "lead": "7+ years",
    "staff": "8+ years",
    "principal": "10+ years",
}

ROLE_STOPWORDS = {
    "and", "for", "the", "with", "in", "to", "of", "a", "an", "engineer", "developer",
    "specialist", "position", "role", "required", "need", "hiring", "looking"
}

def _role_family_label(role: str) -> str:
    role_l = _normalize_free_text(role)
    role_tokens = set(role_l.split())

    if any(token in role_l for token in ("security", "infosec", "cyber")):
        return "Security"
    if (
        "data" in role_tokens
        or "scientist" in role_tokens
        or "analyst" in role_tokens
        or "ml" in role_tokens
        or "ai" in role_tokens
        or "machine learning" in role_l
        or "analytics" in role_l
    ):
        return "Data & AI"
    if any(token in role_l for token in ("backend", "api", "server", "platform engineer")):
        return "Backend Engineering"
    if any(token in role_l for token in ("frontend", "ui", "ux", "web developer")):
        return "Frontend Engineering"
    if any(token in role_l for token in ("fullstack", "full stack")):
        return "Fullstack Engineering"
    if any(token in role_l for token in ("devops", "site reliability", "sre", "cloud architect", "cloud engineer", "infrastructure")):
        return "DevOps / Platform"
    if any(token in role_l for token in ("ios", "android", "mobile", "react native", "flutter")):
        return "Mobile Engineering"
    if any(token in role_l for token in ("qa", "quality", "test", "automation engineer")):
        return "QA / Testing"
    if any(token in role_l for token in ("manager", "product", "designer")):
        return "Product / Design / Management"
    return "Other Engineering"

def _extract_known_skills(text: str, limit: int = 10) -> List[str]:
    normalized = _normalize_free_text(text)
    if not normalized:
        return []

    found: List[str] = []
    for skill in KNOWN_SKILL_TERMS:
        skill_l = skill.lower()
        if len(skill_l) <= 2:
            matched = re.search(rf'\b{re.escape(skill_l)}\b', normalized) is not None
        else:
            matched = skill_l in normalized

        if matched and skill not in found:
            found.append(skill)

        if len(found) >= limit:
            break

    return found

def _infer_role_from_text(text: str) -> str:
    if not text.strip():
        return "Not specified"

    patterns = [
        r'(?:looking for|hiring|seeking|need(?:ing)?|role\s*[:\-])\s+(?:an?\s+)?([a-z0-9+\-/ ]{3,60}?)(?:\s+with|\s+to|\s+for|\s+who|\.|,|\n)',
        r'([a-z0-9+\-/ ]{3,60}(?:engineer|developer|architect|scientist|manager|analyst|designer))',
    ]

    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            role = re.sub(r'\s+', ' ', match.group(1)).strip(" .,-")
            if len(role) >= 3:
                return " ".join(word.capitalize() for word in role.split())

    first_line = text.strip().splitlines()[0][:80]
    if len(first_line.split()) >= 2:
        return first_line.strip(" .,-")
    return "Not specified"

def _infer_seniority(text: str, role: str) -> str:
    source = f"{text} {role}".lower()
    if any(keyword in source for keyword in ["principal", "staff"]):
        return "Lead"
    if any(keyword in source for keyword in ["lead", "head"]):
        return "Lead"
    if "senior" in source:
        return "Senior"
    if "mid" in source:
        return "Mid-Level"
    if any(keyword in source for keyword in ["junior", "entry", "fresher"]):
        return "Junior"
    return "Not specified"

def _infer_experience_required(text: str, seniority: str) -> str:
    match = re.search(r'(\d+)\s*(?:\+|plus)?\s*(?:years|yrs)', text.lower())
    if match:
        return f"{match.group(1)}+ years"

    if seniority.strip().lower() in {"junior", "mid-level", "senior", "lead"}:
        key = seniority.lower().replace("-level", "")
        return SENIORITY_TO_EXPERIENCE.get(key, "Not specified")

    return "Not specified"

def _infer_location(text: str) -> str:
    lowered = text.lower()
    if "remote" in lowered:
        return "Remote"

    patterns = [
        r'(?:location|based in|in)\s*[:\-]?\s*([a-zA-Z][a-zA-Z\s,]{2,50})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            location = re.sub(r'\s+', ' ', match.group(1)).strip(" .,-")
            if len(location) >= 3:
                return location

    return "Not specified"

def _infer_work_location_preference(text: str, parsed_location: Optional[str] = None) -> str:
    source = f"{text or ''} {parsed_location or ''}".strip()
    inferred = _normalize_work_location_preference(source)
    if inferred != WORK_MODE_NOT_SPECIFIED:
        return inferred
    return WORK_MODE_NOT_SPECIFIED

def _build_fallback_jd_response(jd_text: str, error_hint: str) -> JobDescriptionResponse:
    extracted_skills = _extract_known_skills(jd_text, limit=10)
    must_have = extracted_skills[:5]
    good_to_have = extracted_skills[5:10]
    role = _infer_role_from_text(jd_text)
    seniority = _infer_seniority(jd_text, role)
    inferred_location = _infer_location(jd_text)

    compact_error_hint = re.sub(r'\s+', ' ', (error_hint or "")).strip()[:220]
    fallback_warning = (
        "AI parsing degraded. Parsed with heuristic fallback; review extracted fields before matching. "
        f"Cause: {compact_error_hint}"
    )

    summary_sentence = re.split(r'(?<=[.!?])\s+', jd_text.strip())[0] if jd_text.strip() else ""
    summary_sentence = summary_sentence[:220].strip()

    return JobDescriptionResponse(
        role=role,
        experience_required=_infer_experience_required(jd_text, seniority),
        must_have_skills=must_have,
        good_to_have_skills=good_to_have,
        location=inferred_location,
        work_location_preference=_infer_work_location_preference(jd_text, inferred_location),
        seniority=seniority,
        summary=summary_sentence or "Heuristic parse generated from the provided JD text.",
        parse_success=False,
        warning=fallback_warning,
    )

def _extract_required_experience(experience_required: str, seniority: str) -> Optional[int]:
    exp_text = (experience_required or "").lower()
    exp_match = re.search(r'(\d+)', exp_text)
    if exp_match:
        return int(exp_match.group(1))

    seniority_l = (seniority or "").lower()
    if "junior" in seniority_l or "entry" in seniority_l:
        return 1
    if "mid" in seniority_l:
        return 3
    if "senior" in seniority_l:
        return 5
    if "lead" in seniority_l or "staff" in seniority_l or "principal" in seniority_l:
        return 7
    return None

def _normalize_skill(skill: str) -> str:
    return re.sub(r'[^a-z0-9+#.]', '', (skill or '').lower())

def _skills_match(jd_skill: str, candidate_skill: str) -> bool:
    jd_norm = _normalize_skill(jd_skill)
    cand_norm = _normalize_skill(candidate_skill)
    if not jd_norm or not cand_norm:
        return False
    if jd_norm == cand_norm:
        return True

    jd_compact = jd_norm.replace('.', '').replace('-', '')
    cand_compact = cand_norm.replace('.', '').replace('-', '')
    if jd_compact == cand_compact:
        return True

    if len(jd_norm) <= 2 or len(cand_norm) <= 2:
        return False

    return jd_norm in cand_norm or cand_norm in jd_norm

def _role_overlap_ratio(jd_role: str, candidate_role: str) -> float:
    jd_tokens = {
        token for token in _normalize_free_text(jd_role).split()
        if token not in ROLE_STOPWORDS and len(token) > 2
    }
    candidate_tokens = {
        token for token in _normalize_free_text(candidate_role).split()
        if token not in ROLE_STOPWORDS and len(token) > 2
    }

    if not jd_tokens or not candidate_tokens:
        return 0.0

    return len(jd_tokens.intersection(candidate_tokens)) / len(jd_tokens)

def _location_alignment_ratio(jd_location: str, candidate_city: str) -> float:
    jd_geo_tokens = set(_extract_geographic_tokens(jd_location))
    city_tokens = set(_extract_geographic_tokens(candidate_city))

    if not jd_geo_tokens or not city_tokens:
        return 0.0

    if jd_geo_tokens.issubset(city_tokens):
        return 1.0

    overlap = jd_geo_tokens.intersection(city_tokens)
    if len(overlap) >= 2:
        return 0.85
    if len(overlap) == 1:
        return 0.6

    return 0.0

def _work_mode_alignment_ratio(jd_pref: str, candidate_pref: str) -> float:
    jd_work_mode = _normalize_work_location_preference(jd_pref)
    candidate_work_mode = _normalize_work_location_preference(candidate_pref)

    if jd_work_mode == WORK_MODE_NOT_SPECIFIED:
        return 0.0
    if candidate_work_mode == WORK_MODE_NOT_SPECIFIED:
        return 0.4

    if jd_work_mode == WORK_MODE_FLEXIBLE or candidate_work_mode == WORK_MODE_FLEXIBLE:
        return 1.0
    if jd_work_mode == candidate_work_mode:
        return 1.0
    if jd_work_mode == WORK_MODE_HYBRID and candidate_work_mode in {WORK_MODE_REMOTE_ONLY, WORK_MODE_ONSITE_ONLY}:
        return 0.6
    if jd_work_mode in {WORK_MODE_REMOTE_ONLY, WORK_MODE_ONSITE_ONLY} and candidate_work_mode == WORK_MODE_HYBRID:
        return 0.4

    return 0.0

@app.post("/api/parse-jd", response_model=JobDescriptionResponse)
async def parse_jd(request: JobDescriptionRequest):
    if not request.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty")
        
    try:
        prompt = f"""
        You are an expert technical recruiter and AI assistant. Your task is to extract structured information from the provided Job Description.
        
        Analyze the following Job Description and return a JSON object with EXACTLY these fields:
        - "role": (string) The main job title/role.
        - "experience_required": (string) The required years of experience (e.g., "4+ years", "Entry level", "Not specified").
        - "must_have_skills": (list of strings) Up to 10 absolute critical skills required. Keep them concise (e.g., "React", "Next.js").
        - "good_to_have_skills": (list of strings) Up to 10 preferred or bonus skills. Keep them concise.
        - "location": (string) Location, remote status, or "Not specified".
        - "work_location_preference": (string) One of: "Remote only", "On-site only", "Hybrid", "Flexible", or "Not specified".
        - "seniority": (string) Seniority level (e.g., "Junior", "Mid-Level", "Senior", "Lead", "Not specified").
        - "summary": (string) A concise 2-3 sentence summary of the role and its primary objective.
        
        Return ONLY valid JSON. No markdown formatting, no code blocks, just the raw JSON object.
        
        Job Description:
        {request.job_description}
        """

        text = await call_groq_then_gemini(prompt)
        parsed_data = json.loads(_strip_code_fences(text))
        parsed_location = parsed_data.get("location", "Not specified")
        parsed_work_mode = _normalize_work_location_preference(
            parsed_data.get("work_location_preference")
            or _infer_work_location_preference(request.job_description, parsed_location)
        )
        
        # Ensure all fields are present
        return JobDescriptionResponse(
            role=parsed_data.get("role", "Not specified"),
            experience_required=parsed_data.get("experience_required", "Not specified"),
            must_have_skills=parsed_data.get("must_have_skills", []),
            good_to_have_skills=parsed_data.get("good_to_have_skills", []),
            location=parsed_location,
            work_location_preference=parsed_work_mode,
            seniority=parsed_data.get("seniority", "Not specified"),
            summary=parsed_data.get("summary", "Summary not available."),
            parse_success=True,
            warning=None,
        )
        
    except Exception as e:
        print(f"Error parsing JD: {e}")
        return _build_fallback_jd_response(request.job_description, str(e))

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/upload-jd", response_model=JobDescriptionResponse)
async def upload_jd(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    extracted_text = ""
    try:
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        for page in pdf_reader.pages:
            extracted_text += (page.extract_text() or "") + "\n"
            
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

        prompt = f"""
        You are an expert technical recruiter and AI assistant. Your task is to extract structured information from the provided Job Description text extracted from a PDF.
        
        Analyze the following Job Description and return a JSON object with EXACTLY these fields:
        - "role": (string) The main job title/role.
        - "experience_required": (string) The required years of experience (e.g., "4+ years", "Entry level", "Not specified").
        - "must_have_skills": (list of strings) Up to 10 absolute critical skills required. Keep them concise (e.g., "React", "Next.js").
        - "good_to_have_skills": (list of strings) Up to 10 preferred or bonus skills. Keep them concise.
        - "location": (string) Location, remote status, or "Not specified".
        - "work_location_preference": (string) One of: "Remote only", "On-site only", "Hybrid", "Flexible", or "Not specified".
        - "seniority": (string) Seniority level (e.g., "Junior", "Mid-Level", "Senior", "Lead", "Not specified").
        - "summary": (string) A concise 2-3 sentence summary of the role and its primary objective.
        
        Return ONLY valid JSON. No markdown formatting, no code blocks, just the raw JSON object.
        
        Job Description:
        {extracted_text}
        """

        text = await call_groq_then_gemini(prompt)
        parsed_data = json.loads(_strip_code_fences(text))
        parsed_location = parsed_data.get("location", "Not specified")
        parsed_work_mode = _normalize_work_location_preference(
            parsed_data.get("work_location_preference")
            or _infer_work_location_preference(extracted_text, parsed_location)
        )
        
        return JobDescriptionResponse(
            role=parsed_data.get("role", "Not specified"),
            experience_required=parsed_data.get("experience_required", "Not specified"),
            must_have_skills=parsed_data.get("must_have_skills", []),
            good_to_have_skills=parsed_data.get("good_to_have_skills", []),
            location=parsed_location,
            work_location_preference=parsed_work_mode,
            seniority=parsed_data.get("seniority", "Not specified"),
            summary=parsed_data.get("summary", "Summary not available."),
            parse_success=True,
            warning=None,
        )
        
    except Exception as e:
        print(f"Error parsing PDF JD: {e}")
        fallback_source = extracted_text if extracted_text.strip() else file.filename
        return _build_fallback_jd_response(fallback_source, str(e))

class MatchRequest(BaseModel):
    jd_data: JobDescriptionResponse

class ScoreCriterion(BaseModel):
    key: str
    label: str
    weight: float
    evaluated: bool
    achieved_points: float
    achieved_percent: int
    contribution_percent: int
    detail: str

class ScoreBreakdown(BaseModel):
    base_score: int
    final_score: int
    penalty_multiplier: float
    criteria: List[ScoreCriterion]
    penalties: List[str]

class Candidate(BaseModel):
    id: str
    name: str
    role: str
    skills: List[str]
    years_experience: int
    city: str
    remote_preference: str
    work_location_preference: str = WORK_MODE_NOT_SPECIFIED
    expected_salary: str
    education: str
    last_company: str
    open_to_work: bool
    match_score: Optional[int] = 0
    match_reason: Optional[str] = ""
    score_breakdown: Optional[ScoreBreakdown] = None

class MatchResponse(BaseModel):
    candidates: List[Candidate]

class CandidatesResponse(BaseModel):
    source: str
    count: int
    candidates: List[Candidate]

class CountByLabel(BaseModel):
    label: str
    count: int

class CandidateStatsResponse(BaseModel):
    source: str
    total_candidates: int
    open_to_work_candidates: int
    remote_friendly_candidates: int
    average_years_experience: float
    top_roles: List[CountByLabel]
    role_counts: List[CountByLabel]
    role_family_counts: List[CountByLabel]
    top_cities: List[CountByLabel]

@app.get("/api/candidates", response_model=CandidatesResponse)
async def get_candidates(search: Optional[str] = None, work_mode: Optional[str] = None, location: Optional[str] = None):
    try:
        candidates_data, source = await _load_candidates()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No candidates found in database or {MOCK_CANDIDATES_PATH}")

    if search:
        tokens = [token for token in _normalize_free_text(search).split() if token]
        if tokens:
            candidates_data = [
                candidate
                for candidate in candidates_data
                if all(
                    token in _normalize_free_text(
                        " ".join(
                            [
                                str(candidate.get("name", "")),
                                str(candidate.get("role", "")),
                                str(candidate.get("city", "")),
                                str(candidate.get("remote_preference", "")),
                                " ".join(str(skill) for skill in candidate.get("skills", []) if skill),
                            ]
                        )
                    )
                    for token in tokens
                )
            ]

    if work_mode:
        normalized_mode = _normalize_work_location_preference(work_mode)
        if normalized_mode != WORK_MODE_NOT_SPECIFIED:
            candidates_data = [
                candidate
                for candidate in candidates_data
                if _normalize_work_location_preference(candidate.get("work_location_preference")) == normalized_mode
            ]

    if location:
        location_tokens = set(_extract_geographic_tokens(location))
        if location_tokens:
            candidates_data = [
                candidate
                for candidate in candidates_data
                if location_tokens.intersection(set(_extract_geographic_tokens(str(candidate.get("city", "")))))
            ]

    return CandidatesResponse(
        source=source,
        count=len(candidates_data),
        candidates=candidates_data,
    )

@app.get("/api/candidates/stats", response_model=CandidateStatsResponse)
async def get_candidate_stats():
    try:
        candidates_data, source = await _load_candidates()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No candidates found in database or {MOCK_CANDIDATES_PATH}")

    total_candidates = len(candidates_data)
    if total_candidates == 0:
        return CandidateStatsResponse(
            source=source,
            total_candidates=0,
            open_to_work_candidates=0,
            remote_friendly_candidates=0,
            average_years_experience=0.0,
            top_roles=[],
            role_counts=[],
            role_family_counts=[],
            top_cities=[],
        )

    open_to_work_candidates = sum(1 for candidate in candidates_data if candidate.get("open_to_work"))
    remote_friendly_candidates = sum(
        1
        for candidate in candidates_data
        if _normalize_work_location_preference(candidate.get("work_location_preference")) in {
            WORK_MODE_REMOTE_ONLY,
            WORK_MODE_HYBRID,
            WORK_MODE_FLEXIBLE,
        }
    )

    total_experience = sum(int(candidate.get("years_experience", 0) or 0) for candidate in candidates_data)
    average_years_experience = round(total_experience / total_candidates, 1)

    role_counter = Counter(
        str(candidate.get("role", "Unknown Role")).strip() or "Unknown Role"
        for candidate in candidates_data
    )
    city_counter = Counter(
        str(candidate.get("city", "Unknown City")).strip() or "Unknown City"
        for candidate in candidates_data
    )
    role_family_counter = Counter(
        _role_family_label(str(candidate.get("role", "Unknown Role")).strip() or "Unknown Role")
        for candidate in candidates_data
    )

    role_counts = [CountByLabel(label=label, count=count) for label, count in role_counter.most_common()]
    top_roles = [CountByLabel(label=label, count=count) for label, count in role_counter.most_common(5)]
    top_cities = [CountByLabel(label=label, count=count) for label, count in city_counter.most_common(5)]
    role_family_counts = [CountByLabel(label=label, count=count) for label, count in role_family_counter.most_common()]

    return CandidateStatsResponse(
        source=source,
        total_candidates=total_candidates,
        open_to_work_candidates=open_to_work_candidates,
        remote_friendly_candidates=remote_friendly_candidates,
        average_years_experience=average_years_experience,
        top_roles=top_roles,
        role_counts=role_counts,
        role_family_counts=role_family_counts,
        top_cities=top_cities,
    )

@app.post("/api/match-candidates", response_model=MatchResponse)
async def match_candidates(request: MatchRequest):
    try:
        candidates_data, _ = await _load_candidates()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No candidates found in database or {MOCK_CANDIDATES_PATH}")
        
    jd = request.jd_data
    
    jd_required_experience = _extract_required_experience(jd.experience_required, jd.seniority)
    jd_must_skills = [s.strip() for s in jd.must_have_skills if s and s.strip()]
    must_norm = {_normalize_skill(skill) for skill in jd_must_skills}
    jd_good_skills = [
        s.strip()
        for s in jd.good_to_have_skills
        if s and s.strip() and _normalize_skill(s) not in must_norm
    ]
    jd_has_role = not _is_unspecified(jd.role)
    jd_has_geo_location = _has_geographic_location_hint(jd.location)
    jd_work_location_pref = _normalize_work_location_preference(jd.work_location_preference)
    if jd_work_location_pref == WORK_MODE_NOT_SPECIFIED:
        jd_work_location_pref = _normalize_work_location_preference(jd.location)
    jd_has_work_pref = jd_work_location_pref != WORK_MODE_NOT_SPECIFIED
    applicable_criteria = {
        "must": bool(jd_must_skills),
        "good": bool(jd_good_skills),
        "experience": jd_required_experience is not None,
        "location": jd_has_geo_location,
        "role": jd_has_role,
        "work_mode": jd_has_work_pref,
    }

    if not any(applicable_criteria.values()):
        raise HTTPException(
            status_code=400,
            detail="Insufficient JD signals for matching. Please refine the JD input and retry.",
        )

    # Normalize scores only across criteria explicitly present in the JD.
    # Missing signals are not applicable, so they should not cap scores or add penalties.
    weights = {
        "must": 30.0,
        "good": 20.0,
        "experience": 15.0,
        "location": 15.0,
        "role": 10.0,
        "work_mode": 10.0,
    }
    labels = {
        "must": "Must-have Skills",
        "good": "Good-to-have Skills",
        "experience": "Experience Match",
        "location": "Geographic Fit",
        "role": "Role Alignment",
        "work_mode": "Work Mode Fit",
    }
    unavailable_details = {
        "must": "JD did not include must-have skills.",
        "good": "JD did not include good-to-have skills.",
        "experience": "JD did not include explicit experience requirement.",
        "location": "JD did not include specific geographic constraints.",
        "role": "JD role signal was not specific enough.",
        "work_mode": "JD did not include work-location preference.",
    }
    max_points = sum(weight for key, weight in weights.items() if applicable_criteria[key])
    
    scored_candidates = []
    
    for c_data in candidates_data:
        try:
            c = Candidate(**c_data)
        except Exception as e:
            print(f"Skipping malformed candidate record: {e}")
            continue

        score_points = 0.0
        reasons = []
        penalties = []
        criterion_points = {key: 0.0 for key in weights}
        criterion_evaluated = {key: False for key in weights}
        criterion_details = {key: unavailable_details[key] for key in weights}

        candidate_skills = c.skills or []

        if jd_must_skills:
            criterion_evaluated["must"] = True
            must_match_count = sum(
                1 for jd_skill in jd_must_skills
                if any(_skills_match(jd_skill, candidate_skill) for candidate_skill in candidate_skills)
            )
            must_points = (must_match_count / len(jd_must_skills)) * weights["must"]
            criterion_points["must"] = must_points
            criterion_details["must"] = f"Matched {must_match_count} of {len(jd_must_skills)} must-have skills."
            score_points += must_points
            if must_match_count > 0:
                reasons.append(f"Matches {must_match_count}/{len(jd_must_skills)} must-have skills.")

        if jd_good_skills:
            criterion_evaluated["good"] = True
            good_match_count = sum(
                1 for jd_skill in jd_good_skills
                if any(_skills_match(jd_skill, candidate_skill) for candidate_skill in candidate_skills)
            )
            good_points = (good_match_count / len(jd_good_skills)) * weights["good"]
            criterion_points["good"] = good_points
            criterion_details["good"] = f"Matched {good_match_count} of {len(jd_good_skills)} good-to-have skills."
            score_points += good_points
            if good_match_count > 0:
                reasons.append(f"Matches {good_match_count}/{len(jd_good_skills)} good-to-have skills.")

        if jd_required_experience is not None:
            criterion_evaluated["experience"] = True
            exp_diff = c.years_experience - jd_required_experience
            if exp_diff >= 0:
                criterion_points["experience"] = weights["experience"]
                criterion_details["experience"] = (
                    f"Meets requirement with {c.years_experience} years vs required {jd_required_experience}+ years."
                )
                score_points += weights["experience"]
                reasons.append("Meets experience requirement.")
            elif exp_diff >= -1:
                criterion_points["experience"] = weights["experience"] * 0.5
                criterion_details["experience"] = (
                    f"Slightly below requirement ({c.years_experience} years vs {jd_required_experience}+ years)."
                )
                score_points += weights["experience"] * 0.5
                reasons.append("Slightly below experience requirement.")
            else:
                criterion_details["experience"] = (
                    f"Below requirement ({c.years_experience} years vs {jd_required_experience}+ years)."
                )

        location_ratio = 0.0
        if jd_has_geo_location:
            criterion_evaluated["location"] = True
            location_ratio = _location_alignment_ratio(jd.location, c.city)
            location_points = weights["location"] * location_ratio
            criterion_points["location"] = location_points
            if location_ratio >= 0.8:
                criterion_details["location"] = "Strong location alignment with JD geography."
            elif location_ratio >= 0.5:
                criterion_details["location"] = "Partial location alignment with JD geography."
            elif location_ratio > 0:
                criterion_details["location"] = "Weak location alignment with JD geography."
            else:
                criterion_details["location"] = "No geographic overlap with JD location."
            score_points += location_points
            if location_ratio >= 0.8:
                reasons.append("Location aligns strongly with the JD geography.")
            elif location_ratio >= 0.5:
                reasons.append("Location partially aligns with the JD geography.")

        work_mode_ratio = 0.0
        candidate_work_pref = _normalize_work_location_preference(c.work_location_preference or c.remote_preference)
        if jd_has_work_pref:
            criterion_evaluated["work_mode"] = True
            work_mode_ratio = _work_mode_alignment_ratio(jd_work_location_pref, candidate_work_pref)
            work_mode_points = weights["work_mode"] * work_mode_ratio
            criterion_points["work_mode"] = work_mode_points
            if work_mode_ratio >= 0.8:
                criterion_details["work_mode"] = "Work mode aligns strongly with JD preference."
            elif work_mode_ratio >= 0.4:
                criterion_details["work_mode"] = "Work mode partially aligns with JD preference."
            else:
                criterion_details["work_mode"] = "Work mode does not align with JD preference."
            score_points += work_mode_points
            if work_mode_ratio >= 0.8:
                reasons.append("Work-location preference aligns well.")
            elif work_mode_ratio >= 0.4:
                reasons.append("Work-location preference is a partial match.")

        if jd_has_role:
            criterion_evaluated["role"] = True
            role_ratio = _role_overlap_ratio(jd.role, c.role)
            if role_ratio >= 0.6:
                criterion_points["role"] = weights["role"]
                criterion_details["role"] = "Strong role token overlap."
                score_points += weights["role"]
                reasons.append("Strong role alignment.")
            elif role_ratio >= 0.3:
                criterion_points["role"] = weights["role"] * 0.6
                criterion_details["role"] = "Partial role token overlap."
                score_points += weights["role"] * 0.6
                reasons.append("Partial role alignment.")
            else:
                criterion_details["role"] = "Low role token overlap."

        # Keep mismatches inside the weighted criteria. A second multiplier is only
        # defensible when the JD marks a constraint as hard/non-negotiable.
        penalty_multiplier = 1.0

        base_score = int(round((score_points / max_points) * 100)) if max_points > 0 else 0
        final_score = int(round(base_score * penalty_multiplier))
        c.match_score = _clamp_score(final_score, default=0)
        c.match_reason = " ".join(reasons).strip() or "Limited alignment based on currently extracted JD signals."
        c.score_breakdown = ScoreBreakdown(
            base_score=_clamp_score(base_score, default=0),
            final_score=c.match_score,
            penalty_multiplier=round(penalty_multiplier, 2),
            criteria=[
                ScoreCriterion(
                    key=key,
                    label=labels[key],
                    weight=weights[key],
                    evaluated=criterion_evaluated[key],
                    achieved_points=round(criterion_points[key], 2),
                    achieved_percent=_clamp_score(
                        int(round((criterion_points[key] / weights[key]) * 100))
                        if criterion_evaluated[key] and weights[key] > 0
                        else 0,
                        default=0,
                    ),
                    contribution_percent=_clamp_score(
                        int(round((criterion_points[key] / max_points) * 100))
                        if criterion_evaluated[key] and max_points > 0
                        else 0,
                        default=0,
                    ),
                    detail=criterion_details[key],
                )
                for key in weights
            ],
            penalties=penalties,
        )
        scored_candidates.append(c)
        
    # Sort and get top 10
    scored_candidates.sort(key=lambda x: x.match_score, reverse=True)
    top_candidates = scored_candidates[:10]
    
    # Enhance match reasons with Gemini explainability
    try:
        candidates_summary = []
        for i, c in enumerate(top_candidates):
            candidates_summary.append(f"{i+1}. {c.name} - Role: {c.role}, Skills: {', '.join(c.skills[:6])}, YOE: {c.years_experience}, Score: {c.match_score}/100")
        
        explain_prompt = f"""You are a talent matching AI. For each of the following top candidates matched against a Job Description, write a concise 1-sentence explanation of WHY they are a good match.

Job Description:
- Role: {jd.role}
- Must-have: {', '.join(jd.must_have_skills)}
- Good-to-have: {', '.join(jd.good_to_have_skills)}
- Experience: {jd.experience_required}
- Location: {jd.location}
- Work mode preference: {jd_work_location_pref}

Candidates:
{chr(10).join(candidates_summary)}

Return ONLY valid JSON as an array of strings, one explanation per candidate in order. Each explanation should be specific and mention key matching skills or traits. Keep each under 25 words.
Example: ["Strong React/TypeScript match with 7 years experience exceeding the 4+ requirement.", ...]"""

        text = await _generate_gemini_text(explain_prompt, GEMINI_MODEL)
        
        explanations = json.loads(_strip_code_fences(text))
        for i, explanation in enumerate(explanations):
            if i < len(top_candidates):
                top_candidates[i].match_reason = explanation
    except Exception as e:
        print(f"Gemini explainability failed (using fallback reasons): {e}")
    
    return MatchResponse(candidates=top_candidates)

class SimulateInterestRequest(BaseModel):
    candidate: Candidate
    jd_data: JobDescriptionResponse
    candidate_rank: Optional[int] = None
    candidate_pool_size: Optional[int] = None

class ChatMessage(BaseModel):
    sender: str
    message: str

class SimulateInterestResponse(BaseModel):
    chat_logs: List[ChatMessage]
    interest_score: int
    final_score: int
    interest_reason: str = ""
    interest_factors: List[str] = []

def _positive_int_or_none(value) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None

def _engagement_message_count(match_score, candidate_rank: Optional[int] = None, candidate_pool_size: Optional[int] = None) -> int:
    rank = _positive_int_or_none(candidate_rank)
    if rank is not None:
        if rank <= 3:
            return 5
        if rank <= 7:
            return 4
        return 3

    score = _clamp_score(match_score, default=0)
    if score < 55:
        return 3
    if score < 75:
        return 4
    return 5

def _compact_chat_message(message: str, max_chars: int = 220) -> str:
    compact = re.sub(r'\s+', ' ', str(message or "")).strip()
    if len(compact) <= max_chars:
        return compact

    clipped = compact[:max_chars - 3].rsplit(" ", 1)[0].rstrip(" .,")
    return f"{clipped}..." if clipped else compact[:max_chars].rstrip()

def _expected_chat_sender(index: int, candidate_name: str) -> str:
    return "ALIGNA" if index % 2 == 0 else candidate_name

def _build_synthetic_chat_logs(cand: Candidate, jd: JobDescriptionResponse, message_count: int) -> List[ChatMessage]:
    top_skills = ", ".join((cand.skills or [])[:2])
    skill_phrase = f"your {top_skills} background" if top_skills else "your background"
    job_context = jd.location if not _is_unspecified(jd.location) else jd.work_location_preference
    job_context = "" if _is_unspecified(job_context) else f" ({job_context})"

    messages = [
        ChatMessage(
            sender="ALIGNA",
            message=_compact_chat_message(
                f"Hi {cand.name}, I'm reaching out about a {jd.role} role{job_context}. {skill_phrase} looked relevant."
            ),
        ),
        ChatMessage(
            sender=cand.name,
            message=(
                "Thanks. I'm open to hearing more - what's the scope and setup?"
                if cand.open_to_work
                else "Thanks for reaching out. I'm not actively looking, but I can listen if it's a strong fit."
            ),
        ),
        ChatMessage(
            sender="ALIGNA",
            message=_compact_chat_message(
                "Makes sense. The team is checking fit on skills, timing, compensation, and work setup before scheduling calls."
            ),
        ),
        ChatMessage(
            sender=cand.name,
            message=(
                "That helps. I'd want to understand team ownership, compensation range, and interview steps."
                if cand.open_to_work
                else "That helps. Timing may be tough, so I'd need the brief before committing to a call."
            ),
        ),
        ChatMessage(
            sender="ALIGNA",
            message="Fair. I'll send a concise brief and a couple of optional times so you can decide.",
        ),
    ]
    return messages[:message_count]

def _normalize_chat_logs(raw_chat, cand: Candidate, jd: JobDescriptionResponse, message_count: int) -> List[ChatMessage]:
    fallback_logs = _build_synthetic_chat_logs(cand, jd, message_count)
    raw_messages: List[str] = []

    if isinstance(raw_chat, list):
        for item in raw_chat:
            if not isinstance(item, dict):
                continue
            message = _compact_chat_message(str(item.get("message", "")))
            if not message:
                continue
            raw_messages.append(message)
            if len(raw_messages) >= message_count:
                break

    if not raw_messages:
        return fallback_logs

    normalized_chat_logs: List[ChatMessage] = []
    for index in range(message_count):
        message = raw_messages[index] if index < len(raw_messages) else fallback_logs[index].message
        normalized_chat_logs.append(
            ChatMessage(sender=_expected_chat_sender(index, cand.name), message=message)
        )

    return normalized_chat_logs

def _build_interest_explanation(cand: Candidate, jd: JobDescriptionResponse, interest_score: int, match_score: int) -> tuple[str, List[str]]:
    factors: List[str] = []

    if cand.open_to_work:
        factors.append("Candidate is open to work, which increases likely responsiveness.")
    else:
        factors.append("Candidate is not actively open to work, which lowers likely responsiveness.")

    if match_score >= 75:
        factors.append("Strong match score makes the role feel relevant to the candidate.")
    elif match_score >= 55:
        factors.append("Moderate match score suggests some fit, but not a standout match.")
    else:
        factors.append("Lower match score suggests weaker role fit and lower likely interest.")

    jd_work_mode = _normalize_work_location_preference(jd.work_location_preference or jd.location)
    cand_work_mode = _normalize_work_location_preference(cand.work_location_preference or cand.remote_preference)
    if jd_work_mode != WORK_MODE_NOT_SPECIFIED:
        work_ratio = _work_mode_alignment_ratio(jd_work_mode, cand_work_mode)
        if work_ratio >= 0.8:
            factors.append("Work setup aligns with the candidate's stated preference.")
        elif work_ratio > 0:
            factors.append("Work setup is only a partial fit for the candidate.")
        else:
            factors.append("Work setup conflicts with the candidate's preference.")

    if interest_score >= 70:
        reason = "High simulated interest because the candidate appears reachable and the role signals fit their profile."
    elif interest_score >= 40:
        reason = "Moderate simulated interest because there are useful fit signals, but also some uncertainty."
    else:
        reason = "Low simulated interest because the candidate has weak fit or availability signals."

    return reason, factors[:3]

def _is_low_signal_interest_text(text: str) -> bool:
    normalized = _normalize_free_text(text)
    if not normalized:
        return True
    low_signal_phrases = {
        "basic match",
        "basic match and remote preference",
        "basic role match",
        "remote preference match",
        "good fit",
        "seems interested",
    }
    return normalized in low_signal_phrases or normalized.startswith("basic match")

def _normalize_interest_explanation(raw_reason, raw_factors, cand: Candidate, jd: JobDescriptionResponse, interest_score: int, match_score: int) -> tuple[str, List[str]]:
    fallback_reason, fallback_factors = _build_interest_explanation(cand, jd, interest_score, match_score)
    raw_reason_text = _compact_chat_message(str(raw_reason or ""), max_chars=240)
    reason = fallback_reason if _is_low_signal_interest_text(raw_reason_text) else raw_reason_text

    factors: List[str] = []
    if isinstance(raw_factors, list):
        for factor in raw_factors[:3]:
            if isinstance(factor, dict):
                text = factor.get("detail") or factor.get("reason") or factor.get("label") or ""
            else:
                text = str(factor or "")
            compact = _compact_chat_message(text, max_chars=160)
            if compact and not _is_low_signal_interest_text(compact):
                factors.append(compact)

    if not factors:
        factors = fallback_factors

    return reason, factors[:3]

@app.post("/api/simulate-interest", response_model=SimulateInterestResponse)
async def simulate_interest(request: SimulateInterestRequest):
    cand = request.candidate
    jd = request.jd_data
    match_score = _clamp_score(cand.match_score, default=0)
    message_count = _engagement_message_count(match_score, request.candidate_rank, request.candidate_pool_size)
    rank_context = (
        f"{request.candidate_rank} of {request.candidate_pool_size}"
        if request.candidate_rank and request.candidate_pool_size
        else "Not provided"
    )
    
    prompt = f"""You are a hiring simulator. Simulate a brief outreach conversation between an AI Recruiter (ALIGNA) and a tech Candidate.

Candidate Profile:
- Name: {cand.name}
- Role: {cand.role}
- Open to Work: {cand.open_to_work}
- Expected Salary: {cand.expected_salary}
- Remote Preference: {cand.remote_preference}
- Work Location Preference: {cand.work_location_preference}
- Match Score: {cand.match_score}/100
- Shortlist Rank: {rank_context}

Job: {jd.role} in {jd.location}
JD Work Location Preference: {jd.work_location_preference}

Write exactly {message_count} short chat messages and assign an interest_score (0-100).
Conversation length is based on shortlist rank, so higher-ranked candidates get a little more conversation even if their raw score is modest.
Make it feel like a natural back-and-forth text thread: concise, realistic, and not paragraph-like.
Alternate senders, starting with ALIGNA. Use only "ALIGNA" and "{cand.name}" as sender values.
Odd-numbered messages must be from ALIGNA; even-numbered messages must be from {cand.name}.
Each message should be 1-2 short sentences and under 220 characters.
If the candidate is a weaker match, keep the conversation brief and less enthusiastic.
Also explain the interest score with one concise interest_reason and 2-3 short interest_factors.
Return ONLY valid JSON:
{{
    "chat_logs": [
        {{"sender": "ALIGNA", "message": "..."}},
        {{"sender": "{cand.name}", "message": "..."}}
    ],
    "interest_score": <int>,
    "interest_reason": "...",
    "interest_factors": ["...", "..."]
}}"""

    # Try Groq model pool first, then Gemini, then deterministic fallback
    text = None
    for provider, call_fn in [("Groq", call_groq), ("Gemini", call_gemini_with_retry)]:
        try:
            text = await call_fn(prompt)
            break
        except Exception as e:
            print(f"{provider} failed for simulate-interest: {e}")
            continue
    
    if text:
        try:
            data = json.loads(_strip_code_fences(text))
            interest = _clamp_score(data.get("interest_score", 50), default=50)

            normalized_chat_logs = _normalize_chat_logs(data.get("chat_logs", []), cand, jd, message_count)
            interest_reason, interest_factors = _normalize_interest_explanation(
                data.get("interest_reason") or data.get("reason"),
                data.get("interest_factors") or data.get("factors"),
                cand,
                jd,
                interest,
                match_score,
            )

            final = _clamp_score(round(0.7 * match_score + 0.3 * interest), default=0)
            
            return SimulateInterestResponse(
                chat_logs=normalized_chat_logs,
                interest_score=interest,
                final_score=final,
                interest_reason=interest_reason,
                interest_factors=interest_factors,
            )
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
    
    # Graceful fallback: synthetic response
    print(f"All providers failed for {cand.name}, using synthetic fallback")
    interest = 70 if cand.open_to_work else 35
    jd_work_mode = _normalize_work_location_preference(jd.work_location_preference or jd.location)
    cand_work_mode = _normalize_work_location_preference(cand.work_location_preference or cand.remote_preference)
    if jd_work_mode == WORK_MODE_ONSITE_ONLY and cand_work_mode == WORK_MODE_REMOTE_ONLY:
        interest = max(interest - 30, 10)
    elif jd_work_mode == WORK_MODE_REMOTE_ONLY and cand_work_mode == WORK_MODE_ONSITE_ONLY:
        interest = max(interest - 25, 10)
    elif jd_work_mode == WORK_MODE_HYBRID and cand_work_mode in {WORK_MODE_REMOTE_ONLY, WORK_MODE_ONSITE_ONLY}:
        interest = max(interest - 12, 10)

    interest = _clamp_score(interest, default=50)
    final = _clamp_score(round(0.7 * match_score + 0.3 * interest), default=0)
    interest_reason, interest_factors = _build_interest_explanation(cand, jd, interest, match_score)
    
    return SimulateInterestResponse(
        chat_logs=_build_synthetic_chat_logs(cand, jd, message_count),
        interest_score=interest,
        final_score=final,
        interest_reason=interest_reason,
        interest_factors=interest_factors,
    )
