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
        "not specified",
        "not mentioned",
        "n/a",
        "na",
        "unknown",
        "unknown role",
    }

def _normalize_free_text(value: str) -> str:
    return re.sub(r'[^a-z0-9+#.\s]+', ' ', (value or '').lower()).strip()

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
        db = db_client.scoutiq
        print("MongoDB URI configured. Connection will be validated on first read.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")

app = FastAPI(title="ScoutIQ Backend", version="1.0.0")

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

def _build_fallback_jd_response(jd_text: str, error_hint: str) -> JobDescriptionResponse:
    extracted_skills = _extract_known_skills(jd_text, limit=10)
    must_have = extracted_skills[:5]
    good_to_have = extracted_skills[5:10]
    role = _infer_role_from_text(jd_text)
    seniority = _infer_seniority(jd_text, role)

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
        location=_infer_location(jd_text),
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

def _location_alignment_ratio(jd_location: str, candidate_city: str, remote_preference: str) -> float:
    jd_loc = _normalize_free_text(jd_location)
    city = _normalize_free_text(candidate_city)
    remote_pref = _normalize_free_text(remote_preference)

    if not jd_loc or _is_unspecified(jd_location):
        return 0.0

    if "remote" in jd_loc:
        if "remote" in remote_pref or "any" in remote_pref:
            return 1.0
        if "hybrid" in remote_pref:
            return 0.6
        return 0.0

    if city and (city in jd_loc or jd_loc in city):
        return 1.0

    jd_tokens = set(jd_loc.split())
    city_tokens = set(city.split())
    if jd_tokens and city_tokens and len(jd_tokens.intersection(city_tokens)) >= 1:
        return 0.6

    if "hybrid" in remote_pref or "any" in remote_pref:
        return 0.3

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
        - "seniority": (string) Seniority level (e.g., "Junior", "Mid-Level", "Senior", "Lead", "Not specified").
        - "summary": (string) A concise 2-3 sentence summary of the role and its primary objective.
        
        Return ONLY valid JSON. No markdown formatting, no code blocks, just the raw JSON object.
        
        Job Description:
        {request.job_description}
        """

        text = await call_groq_then_gemini(prompt)
        parsed_data = json.loads(_strip_code_fences(text))
        
        # Ensure all fields are present
        return JobDescriptionResponse(
            role=parsed_data.get("role", "Not specified"),
            experience_required=parsed_data.get("experience_required", "Not specified"),
            must_have_skills=parsed_data.get("must_have_skills", []),
            good_to_have_skills=parsed_data.get("good_to_have_skills", []),
            location=parsed_data.get("location", "Not specified"),
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
        - "seniority": (string) Seniority level (e.g., "Junior", "Mid-Level", "Senior", "Lead", "Not specified").
        - "summary": (string) A concise 2-3 sentence summary of the role and its primary objective.
        
        Return ONLY valid JSON. No markdown formatting, no code blocks, just the raw JSON object.
        
        Job Description:
        {extracted_text}
        """

        text = await call_groq_then_gemini(prompt)
        parsed_data = json.loads(_strip_code_fences(text))
        
        return JobDescriptionResponse(
            role=parsed_data.get("role", "Not specified"),
            experience_required=parsed_data.get("experience_required", "Not specified"),
            must_have_skills=parsed_data.get("must_have_skills", []),
            good_to_have_skills=parsed_data.get("good_to_have_skills", []),
            location=parsed_data.get("location", "Not specified"),
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

class Candidate(BaseModel):
    id: str
    name: str
    role: str
    skills: List[str]
    years_experience: int
    city: str
    remote_preference: str
    expected_salary: str
    education: str
    last_company: str
    open_to_work: bool
    match_score: Optional[int] = 0
    match_reason: Optional[str] = ""

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
    top_cities: List[CountByLabel]

@app.get("/api/candidates", response_model=CandidatesResponse)
async def get_candidates():
    try:
        candidates_data, source = await _load_candidates()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No candidates found in database or {MOCK_CANDIDATES_PATH}")

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
            top_cities=[],
        )

    open_to_work_candidates = sum(1 for candidate in candidates_data if candidate.get("open_to_work"))
    remote_friendly_candidates = sum(
        1
        for candidate in candidates_data
        if any(
            marker in str(candidate.get("remote_preference", "")).lower()
            for marker in ("remote", "hybrid", "any")
        )
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

    top_roles = [CountByLabel(label=label, count=count) for label, count in role_counter.most_common(5)]
    top_cities = [CountByLabel(label=label, count=count) for label, count in city_counter.most_common(5)]

    return CandidateStatsResponse(
        source=source,
        total_candidates=total_candidates,
        open_to_work_candidates=open_to_work_candidates,
        remote_friendly_candidates=remote_friendly_candidates,
        average_years_experience=average_years_experience,
        top_roles=top_roles,
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
    jd_has_location = not _is_unspecified(jd.location)

    if not (jd_must_skills or jd_good_skills or jd_required_experience is not None or jd_has_role or jd_has_location):
        raise HTTPException(
            status_code=400,
            detail="Insufficient JD signals for matching. Please refine the JD input and retry.",
        )

    # Hardened weights: missing JD signals do not reduce the denominator,
    # effectively capping the maximum possible match score for sparse JDs.
    weights = {
        "must": 40.0,
        "good": 20.0,
        "experience": 20.0,
        "location": 10.0,
        "role": 10.0,
    }
    max_points = 100.0
    
    scored_candidates = []
    
    for c_data in candidates_data:
        try:
            c = Candidate(**c_data)
        except Exception as e:
            print(f"Skipping malformed candidate record: {e}")
            continue

        score_points = 0.0
        reasons = []

        candidate_skills = c.skills or []

        if jd_must_skills:
            must_match_count = sum(
                1 for jd_skill in jd_must_skills
                if any(_skills_match(jd_skill, candidate_skill) for candidate_skill in candidate_skills)
            )
            score_points += (must_match_count / len(jd_must_skills)) * weights["must"]
            if must_match_count > 0:
                reasons.append(f"Matches {must_match_count}/{len(jd_must_skills)} must-have skills.")

        if jd_good_skills:
            good_match_count = sum(
                1 for jd_skill in jd_good_skills
                if any(_skills_match(jd_skill, candidate_skill) for candidate_skill in candidate_skills)
            )
            score_points += (good_match_count / len(jd_good_skills)) * weights["good"]
            if good_match_count > 0:
                reasons.append(f"Matches {good_match_count}/{len(jd_good_skills)} good-to-have skills.")

        if jd_required_experience is not None:
            exp_diff = c.years_experience - jd_required_experience
            if exp_diff >= 0:
                score_points += weights["experience"]
                reasons.append("Meets experience requirement.")
            elif exp_diff >= -1:
                score_points += weights["experience"] * 0.5
                reasons.append("Slightly below experience requirement.")

        if jd_has_location:
            location_ratio = _location_alignment_ratio(jd.location, c.city, c.remote_preference)
            score_points += weights["location"] * location_ratio
            if location_ratio >= 0.8:
                reasons.append("Location preference aligns well.")
            elif location_ratio >= 0.3:
                reasons.append("Location preference partially aligns.")

        if jd_has_role:
            role_ratio = _role_overlap_ratio(jd.role, c.role)
            if role_ratio >= 0.6:
                score_points += weights["role"]
                reasons.append("Strong role alignment.")
            elif role_ratio >= 0.3:
                score_points += weights["role"] * 0.6
                reasons.append("Partial role alignment.")

        normalized_score = int(round((score_points / max_points) * 100))
        c.match_score = _clamp_score(normalized_score, default=0)
        c.match_reason = " ".join(reasons).strip() or "Limited alignment based on currently extracted JD signals."
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

class ChatMessage(BaseModel):
    sender: str
    message: str

class SimulateInterestResponse(BaseModel):
    chat_logs: List[ChatMessage]
    interest_score: int
    final_score: int

@app.post("/api/simulate-interest", response_model=SimulateInterestResponse)
async def simulate_interest(request: SimulateInterestRequest):
    cand = request.candidate
    jd = request.jd_data
    
    prompt = f"""You are a hiring simulator. Simulate a brief outreach conversation between an AI Recruiter (ScoutIQ) and a tech Candidate.

Candidate Profile:
- Name: {cand.name}
- Role: {cand.role}
- Open to Work: {cand.open_to_work}
- Expected Salary: {cand.expected_salary}
- Remote Preference: {cand.remote_preference}
- Match Score: {cand.match_score}/100

Job: {jd.role} in {jd.location}

Write a 3-message chat and assign an interest_score (0-100).
Return ONLY valid JSON:
{{
    "chat_logs": [
        {{"sender": "ScoutIQ", "message": "..."}},
        {{"sender": "{cand.name}", "message": "..."}},
        {{"sender": "ScoutIQ", "message": "..."}}
    ],
    "interest_score": <int>
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

            raw_chat = data.get("chat_logs", [])
            normalized_chat_logs: List[ChatMessage] = []
            if isinstance(raw_chat, list):
                for item in raw_chat[:6]:
                    if not isinstance(item, dict):
                        continue
                    sender = str(item.get("sender", "Candidate")).strip()[:40] or "Candidate"
                    message = str(item.get("message", "")).strip()
                    if not message:
                        continue
                    normalized_chat_logs.append(ChatMessage(sender=sender, message=message))

            if not normalized_chat_logs:
                normalized_chat_logs = [
                    ChatMessage(sender="ScoutIQ", message=f"Hi {cand.name}, we'd love to discuss our {jd.role} opportunity with you."),
                    ChatMessage(sender=cand.name, message="Thanks for sharing details. I am interested in learning more."),
                    ChatMessage(sender="ScoutIQ", message="Great, let's schedule a quick call to explore fit and next steps."),
                ]

            match_score = _clamp_score(cand.match_score, default=0)
            final = _clamp_score(round(0.7 * match_score + 0.3 * interest), default=0)
            
            return SimulateInterestResponse(
                chat_logs=normalized_chat_logs,
                interest_score=interest,
                final_score=final
            )
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
    
    # Graceful fallback: synthetic response
    print(f"All providers failed for {cand.name}, using synthetic fallback")
    interest = 70 if cand.open_to_work else 35
    if "remote" in cand.remote_preference.lower() and "remote" not in jd.location.lower() and jd.location.lower() != "not specified":
        interest = max(interest - 30, 10)

    interest = _clamp_score(interest, default=50)
    match_score = _clamp_score(cand.match_score, default=0)
    final = _clamp_score(round(0.7 * match_score + 0.3 * interest), default=0)
    
    return SimulateInterestResponse(
        chat_logs=[
            ChatMessage(sender="ScoutIQ", message=f"Hi {cand.name}! We found your profile impressive and think you'd be a great fit for our {jd.role} position. Your background in {', '.join(cand.skills[:3])} really stands out."),
            ChatMessage(sender=cand.name, message=f"{'Thanks for reaching out! I am currently open to new opportunities and this sounds interesting.' if cand.open_to_work else 'I appreciate the outreach. I am not actively looking right now, but I would be open to hearing more about the role.'}"),
            ChatMessage(sender="ScoutIQ", message=f"Great to hear! I will send over the full job details and we can schedule a call to discuss further. Looking forward to connecting!")
        ],
        interest_score=interest,
        final_score=final
    )
