import sys
import os
import json
import asyncio

# Add the project root to the python path so we can import from api
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from api.index import _clamp_score, _skills_match, _location_alignment_ratio

def test_clamping():
    print("Testing score clamping...")
    assert _clamp_score(150) == 100
    assert _clamp_score(-10) == 0
    assert _clamp_score(50) == 50
    assert _clamp_score("75") == 75
    assert _clamp_score("abc", default=50) == 50
    print("✓ Clamping tests passed")

def test_skill_matching():
    print("Testing skill matching...")
    assert _skills_match("React.js", "react") == True
    assert _skills_match("Node", "Node.js") == True
    assert _skills_match("Python", "Java") == False
    assert _skills_match("AWS", "Cloud") == False
    print("✓ Skill matching tests passed")

def test_location_alignment():
    print("Testing location alignment...")
    # Remote JD
    assert _location_alignment_ratio("Remote", "New York", "Remote") == 1.0
    assert _location_alignment_ratio("Remote", "New York", "On-site") == 0.0
    
    # Specific City JD
    assert _location_alignment_ratio("San Francisco", "San Francisco", "On-site") == 1.0
    assert _location_alignment_ratio("San Francisco", "Oakland", "Any") == 0.3 # Partial
    print("✓ Location alignment tests passed")

if __name__ == "__main__":
    try:
        test_clamping()
        test_skill_matching()
        test_location_alignment()
        print("\nAll backend logic tests passed successfully!")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")
        sys.exit(1)
