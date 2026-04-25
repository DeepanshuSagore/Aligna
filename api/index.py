import os
import json
import re
import io
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import google.generativeai as genai
from groq import Groq
from motor.motor_asyncio import AsyncIOMotorClient
import PyPDF2
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.local")

# Gemini model - used for JD parsing (low volume)
GEMINI_MODEL = 'gemini-2.0-flash'

# Groq config - used for simulation (high volume, fast, generous free tier)
GROQ_MODEL = 'llama-3.3-70b-versatile'
groq_key = os.getenv("GROQ_API_KEY")
groq_client = None
if groq_key:
    groq_client = Groq(api_key=groq_key)
    print(f"Groq configured with model: {GROQ_MODEL}")
else:
    print("WARNING: GROQ_API_KEY not found. Will fall back to Gemini for simulations.")

async def call_groq(prompt: str) -> str:
    """Call Groq API for fast LLM inference."""
    if not groq_client:
        raise Exception("Groq client not configured")
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()

async def call_gemini_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Call Gemini API with retry logic for rate limits."""
    model = genai.GenerativeModel(GEMINI_MODEL)
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            error_str = str(e)
            if '429' in error_str and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"Gemini rate limited, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                raise e
    raise Exception("Max retries exceeded")

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
        db_client = AsyncIOMotorClient(mongo_uri)
        db = db_client.scoutiq
        print("Connected to MongoDB Atlas successfully.")
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

@app.post("/api/parse-jd", response_model=JobDescriptionResponse)
async def parse_jd(request: JobDescriptionRequest):
    if not request.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty")
        
    try:
        # Use Gemini to parse the JD
        model = genai.GenerativeModel(GEMINI_MODEL)
        
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
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean up if Gemini returned markdown code block
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        parsed_data = json.loads(text.strip())
        
        # Ensure all fields are present
        return JobDescriptionResponse(
            role=parsed_data.get("role", "Not specified"),
            experience_required=parsed_data.get("experience_required", "Not specified"),
            must_have_skills=parsed_data.get("must_have_skills", []),
            good_to_have_skills=parsed_data.get("good_to_have_skills", []),
            location=parsed_data.get("location", "Not specified"),
            seniority=parsed_data.get("seniority", "Not specified"),
            summary=parsed_data.get("summary", "Summary not available.")
        )
        
    except Exception as e:
        print(f"Error parsing JD: {e}")
        # Safe fallback
        return JobDescriptionResponse(
            role="Unknown Role",
            experience_required="Not specified",
            must_have_skills=[],
            good_to_have_skills=[],
            location="Not specified",
            seniority="Not specified",
            summary="Could not automatically parse the job description. Please review it manually."
        )

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/upload-jd", response_model=JobDescriptionResponse)
async def upload_jd(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    try:
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() + "\n"
            
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
            
        model = genai.GenerativeModel(GEMINI_MODEL)
        
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
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
            
        parsed_data = json.loads(text.strip())
        
        return JobDescriptionResponse(
            role=parsed_data.get("role", "Not specified"),
            experience_required=parsed_data.get("experience_required", "Not specified"),
            must_have_skills=parsed_data.get("must_have_skills", []),
            good_to_have_skills=parsed_data.get("good_to_have_skills", []),
            location=parsed_data.get("location", "Not specified"),
            seniority=parsed_data.get("seniority", "Not specified"),
            summary=parsed_data.get("summary", "Summary not available.")
        )
        
    except Exception as e:
        print(f"Error parsing PDF JD: {e}")
        return JobDescriptionResponse(
            role="Unknown Role",
            experience_required="Not specified",
            must_have_skills=[],
            good_to_have_skills=[],
            location="Not specified",
            seniority="Not specified",
            summary="Could not automatically parse the PDF job description. Please review it manually."
        )

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

@app.post("/api/match-candidates", response_model=MatchResponse)
async def match_candidates(request: MatchRequest):
    candidates_data = []
    
    if db is not None:
        try:
            cursor = db.candidates.find({})
            async for doc in cursor:
                doc['id'] = str(doc.pop('_id')) if '_id' in doc and 'id' not in doc else doc.get('id', str(doc.get('_id')))
                candidates_data.append(doc)
        except Exception as e:
            print(f"MongoDB read error: {e}")
            candidates_data = []
            
    # Fallback to JSON
    if not candidates_data:
        try:
            with open("mock_candidates.json", "r") as f:
                candidates_data = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="No candidates found in database or mock_candidates.json")
        
    jd = request.jd_data
    
    # Simple parsing of JD experience required
    jd_exp = 0
    exp_match = re.search(r'(\d+)', jd.experience_required)
    if exp_match:
        jd_exp = int(exp_match.group(1))
    
    jd_must_skills = [s.lower() for s in jd.must_have_skills]
    jd_good_skills = [s.lower() for s in jd.good_to_have_skills]
    
    scored_candidates = []
    
    for c_data in candidates_data:
        c = Candidate(**c_data)
        score = 0
        reasons = []
        
        # 1. Skill Score (60 points max)
        c_skills = [s.lower() for s in c.skills]
        must_match_count = sum(1 for s in jd_must_skills if any(s in cs or cs in s for cs in c_skills))
        good_match_count = sum(1 for s in jd_good_skills if any(s in cs or cs in s for cs in c_skills))
        
        must_score = (must_match_count / max(len(jd_must_skills), 1)) * 40 if jd_must_skills else 40
        good_score = (good_match_count / max(len(jd_good_skills), 1)) * 20 if jd_good_skills else 20
        
        score += must_score + good_score
        if must_match_count > 0:
            reasons.append(f"Matches {must_match_count} required skills.")
            
        # 2. Experience Score (20 points max)
        exp_diff = c.years_experience - jd_exp
        if exp_diff >= 0:
            score += 20
            reasons.append("Meets experience requirements.")
        elif exp_diff >= -1:
            score += 10
        else:
            score += 0
            
        # 3. Location/Role Score (20 points max)
        jd_loc = jd.location.lower()
        if "remote" in jd_loc and "remote" in c.remote_preference.lower():
            score += 10
        elif jd_loc != "not specified" and (c.city.lower() in jd_loc or jd_loc in c.city.lower()):
            score += 10
        else:
            score += 5 # default points if location not strictly specified or matched
            
        jd_role_words = set(jd.role.lower().split())
        c_role_words = set(c.role.lower().split())
        if len(jd_role_words.intersection(c_role_words)) > 0:
            score += 10
            reasons.append("Strong role match.")
            
        c.match_score = min(int(score), 100)
        c.match_reason = " ".join(reasons).strip()
        scored_candidates.append(c)
        
    # Sort and get top 10
    scored_candidates.sort(key=lambda x: x.match_score, reverse=True)
    top_candidates = scored_candidates[:10]
    
    # Enhance match reasons with Gemini explainability
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
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

        response = model.generate_content(explain_prompt)
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        
        explanations = json.loads(text.strip())
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

    # Try Groq first (fast, generous free tier), then Gemini, then fallback
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
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            
            data = json.loads(text.strip())
            interest = data.get("interest_score", 50)
            chat = data.get("chat_logs", [])
            
            final = int(0.7 * cand.match_score + 0.3 * interest)
            
            return SimulateInterestResponse(
                chat_logs=chat,
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
    
    final = int(0.7 * cand.match_score + 0.3 * interest)
    
    return SimulateInterestResponse(
        chat_logs=[
            ChatMessage(sender="ScoutIQ", message=f"Hi {cand.name}! We found your profile impressive and think you'd be a great fit for our {jd.role} position. Your background in {', '.join(cand.skills[:3])} really stands out."),
            ChatMessage(sender=cand.name, message=f"{'Thanks for reaching out! I am currently open to new opportunities and this sounds interesting.' if cand.open_to_work else 'I appreciate the outreach. I am not actively looking right now, but I would be open to hearing more about the role.'}"),
            ChatMessage(sender="ScoutIQ", message=f"Great to hear! I will send over the full job details and we can schedule a call to discuss further. Looking forward to connecting!")
        ],
        interest_score=interest,
        final_score=final
    )
