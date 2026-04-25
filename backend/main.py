import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import google.generativeai as genai
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../../.env.local")
load_dotenv("../.env.local")
load_dotenv(".env.local")
load_dotenv() # also load local .env if exists

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

@app.post("/parse-jd", response_model=JobDescriptionResponse)
async def parse_jd(request: JobDescriptionRequest):
    if not request.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty")
        
    try:
        # Use Gemini to parse the JD
        model = genai.GenerativeModel('gemini-2.5-pro')
        
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

@app.get("/health")
def health_check():
    return {"status": "healthy"}

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

@app.post("/match-candidates", response_model=MatchResponse)
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

@app.post("/simulate-interest", response_model=SimulateInterestResponse)
async def simulate_interest(request: SimulateInterestRequest):
    cand = request.candidate
    jd = request.jd_data
    
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        prompt = f"""
        You are a hiring simulator. Your job is to simulate a brief outreach conversation between an AI Recruiter (ScoutIQ) and a tech Candidate.
        
        Candidate Profile:
        - Name: {cand.name}
        - Role: {cand.role}
        - Open to Work: {cand.open_to_work}
        - Expected Salary: {cand.expected_salary}
        - Remote Preference: {cand.remote_preference}
        - Current Match Score with JD: {cand.match_score}/100
        
        Job Description Context:
        - Role: {jd.role}
        - Location: {jd.location}
        
        Task:
        1. Write a 3-message chat log:
           Message 1 (ScoutIQ): A brief, personalized outreach mentioning their skills and the role.
           Message 2 ({cand.name}): The candidate's response based realistically on their profile (e.g. if they want remote and JD is on-site, they might decline. If open to work, they might be eager).
           Message 3 (ScoutIQ): A brief wrap-up or next steps.
        2. Assign an "interest_score" (0 to 100) based on how positive/eager their response was.
        
        Return ONLY valid JSON with EXACTLY this structure:
        {{
            "chat_logs": [
                {{"sender": "ScoutIQ", "message": "..."}},
                {{"sender": "{cand.name}", "message": "..."}},
                {{"sender": "ScoutIQ", "message": "..."}}
            ],
            "interest_score": <int>
        }}
        """
        
        response = model.generate_content(prompt)
        text = response.text.strip()
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
    except Exception as e:
        print(f"Error simulating interest: {e}")
        raise HTTPException(status_code=500, detail="Failed to simulate interest")

