import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, ".env.local"))

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY not found in environment. Please add it to your .env.local file.")
    exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

def generate_batch(batch_num, num_candidates=30):
    prompt = f"""
    You are an expert technical recruiter and data generator.
    Generate a JSON array of {num_candidates} highly realistic tech candidate profiles.
    
    Make the data extremely varied. Include different tech stacks (Frontend, Backend, Fullstack, Data, DevOps, Mobile, AI/ML).
    Vary their experience levels from 1 to 15 years.
    Make the names realistic and diverse.
    Vary the locations (major tech hubs, remote, different countries).
    
    Return ONLY a raw JSON array. Do not use markdown blocks like ```json. Just return the JSON.
    
    Each object in the array must have EXACTLY these fields:
    - "id": a unique string (e.g. "cand_batch{batch_num}_" + random digits)
    - "name": string
    - "role": string (e.g. "Senior Frontend Engineer", "Data Scientist", "Backend Developer")
    - "skills": array of strings (5-10 technical skills)
    - "years_experience": integer
    - "city": string (e.g. "San Francisco, CA", "London, UK", "Remote", "Bengaluru, India")
    - "remote_preference": string ("Remote only", "Hybrid", "On-site", "Any")
    - "expected_salary": string (e.g. "$120,000", "€80,000", "₹30,00,000")
    - "education": string (e.g. "B.S. Computer Science", "Self-taught", "M.S. Data Science")
    - "last_company": string (Make up realistic sounding company names or use well known ones)
    - "open_to_work": boolean (true/false)
    """
    
    print(f"Requesting batch {batch_num} from Gemini...")
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean up if Gemini returned markdown code block
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        candidates = json.loads(text.strip())
        return candidates
    except Exception as e:
        print(f"Error in batch {batch_num}: {e}")
        return []

def main():
    all_candidates = []
    total_batches = 5
    
    print("Starting generation of 150 candidates using Gemini...")
    for i in range(1, total_batches + 1):
        batch = generate_batch(i, 30)
        all_candidates.extend(batch)
        print(f"Batch {i} generated {len(batch)} candidates. Total so far: {len(all_candidates)}")
        
        if i < total_batches:
            # Sleep to avoid rate limits
            print("Sleeping for 10 seconds to respect rate limits...")
            time.sleep(10)
            
    # Deduplicate just in case
    unique_candidates = {c['id']: c for c in all_candidates if 'id' in c}
    final_list = list(unique_candidates.values())
    
    # Save to file
    output_path = os.path.join(PROJECT_ROOT, "mock_candidates.json")
    with open(output_path, "w") as f:
        json.dump(final_list, f, indent=2)
        
    print(f"Successfully saved {len(final_list)} candidates to {output_path}")

if __name__ == "__main__":
    main()
