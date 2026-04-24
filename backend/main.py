import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../../.env.local")
load_dotenv() # also load local .env if exists

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("WARNING: GEMINI_API_KEY not found in environment.")
else:
    genai.configure(api_key=api_key)

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
        model = genai.GenerativeModel('gemini-1.5-pro')
        
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
