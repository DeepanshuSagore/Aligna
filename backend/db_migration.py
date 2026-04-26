import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env.local"))

def migrate_database():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("❌ ERROR: MONGODB_URI not found in .env.local")
        return

    print("🔗 Connecting to MongoDB...")
    client = MongoClient(uri)
    
    source_db = client.scoutiq
    target_db = client.aligna
    
    source_coll = source_db.candidates
    target_coll = target_db.candidates
    
    # Count documents in source
    count = source_coll.count_documents({})
    if count == 0:
        print("⚠️ No documents found in 'scoutiq.candidates'. Nothing to migrate.")
        return

    print(f"📦 Found {count} candidates in 'scoutiq.candidates'.")
    print(f"🚀 Migrating to 'aligna.candidates'...")
    
    # Fetch all documents
    candidates = list(source_coll.find({}))
    
    # Clear target collection just in case
    target_coll.delete_many({})
    
    # Insert into target
    if candidates:
        result = target_coll.insert_many(candidates)
        print(f"✅ Successfully migrated {len(result.inserted_ids)} candidates to 'aligna' database.")
        print("\nNote: The old 'scoutiq' database still exists. You can delete it manually in Atlas if you want.")
    else:
        print("❓ No candidates retrieved. Migration skipped.")

if __name__ == "__main__":
    migrate_database()
