import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, ".env.local"))

uri = os.getenv("MONGODB_URI")
if not uri:
    print("ERROR: MONGODB_URI not found.")
    exit(1)

client = MongoClient(uri)
# Using 'aligna' database
db = client.aligna
collection = db.candidates

def migrate():
    # Load candidates from JSON
    try:
        with open(os.path.join(PROJECT_ROOT, "mock_candidates.json"), "r") as f:
            candidates = json.load(f)
    except FileNotFoundError:
        print("ERROR: mock_candidates.json not found.")
        return

    print(f"Loaded {len(candidates)} candidates from JSON.")
    
    # Optional: Clear existing collection to avoid duplicates if re-running
    collection.delete_many({})
    print("Cleared existing candidates in MongoDB.")
    
    # Insert candidates
    if candidates:
        result = collection.insert_many(candidates)
        print(f"Successfully inserted {len(result.inserted_ids)} candidates into MongoDB.")
    else:
        print("No candidates to insert.")

if __name__ == "__main__":
    migrate()
