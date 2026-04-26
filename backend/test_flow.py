import sys
import os
import asyncio

# Add the project root to the python path so we can import from api
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

import api.index as api_index

def test_clamping():
    print("Testing score clamping...")
    assert api_index._clamp_score(150) == 100
    assert api_index._clamp_score(-10) == 0
    assert api_index._clamp_score(50) == 50
    assert api_index._clamp_score("75") == 75
    assert api_index._clamp_score("abc", default=50) == 50
    print("✓ Clamping tests passed")

def test_skill_matching():
    print("Testing skill matching...")
    assert api_index._skills_match("React.js", "react") == True
    assert api_index._skills_match("Node", "Node.js") == True
    assert api_index._skills_match("Python", "Java") == False
    assert api_index._skills_match("AWS", "Cloud") == False
    print("✓ Skill matching tests passed")

def test_location_alignment():
    print("Testing location alignment...")
    # Remote is handled by work-mode scoring, not geographic scoring.
    assert api_index._location_alignment_ratio("Remote", "New York") == 0.0
    assert api_index._location_alignment_ratio("Not specified", "Austin, TX") == 0.0
    assert api_index._location_alignment_ratio("No preference", "Austin, TX") == 0.0
    assert api_index._location_alignment_ratio("Flexible", "Austin, TX") == 0.0
    
    # Specific City JD
    assert api_index._location_alignment_ratio("San Francisco, CA", "San Francisco, CA") == 1.0
    assert api_index._location_alignment_ratio("San Francisco, CA", "Los Angeles, CA") == 0.85
    print("✓ Location alignment tests passed")

def test_work_mode_alignment():
    print("Testing work-mode alignment...")
    assert api_index._work_mode_alignment_ratio("Remote only", "Remote only") == 1.0
    assert api_index._work_mode_alignment_ratio("Hybrid", "Remote only") == 0.6
    assert api_index._work_mode_alignment_ratio("Remote only", "On-site only") == 0.0
    assert api_index._work_mode_alignment_ratio("Not specified", "Remote only") == 0.0
    print("✓ Work-mode alignment tests passed")

def _sample_candidate(match_score=80, open_to_work=True):
    return api_index.Candidate(
        id="cand-1",
        name="Ava Chen",
        role="Frontend Engineer",
        skills=["React", "TypeScript"],
        years_experience=6,
        city="Austin, TX",
        remote_preference="Remote only",
        work_location_preference="Remote only",
        expected_salary="$150k",
        education="BS Computer Science",
        last_company="Acme",
        open_to_work=open_to_work,
        match_score=match_score,
    )

def _sample_jd():
    return api_index.JobDescriptionResponse(
        role="Frontend Engineer",
        experience_required="5+ years",
        must_have_skills=["React"],
        good_to_have_skills=[],
        location="Not specified",
        work_location_preference=api_index.WORK_MODE_NOT_SPECIFIED,
        seniority="Senior",
        summary="Frontend role focused on React.",
    )

def test_engagement_message_count():
    print("Testing engagement message count...")
    assert api_index._engagement_message_count(20) == 3
    assert api_index._engagement_message_count(54) == 3
    assert api_index._engagement_message_count(55) == 4
    assert api_index._engagement_message_count(74) == 4
    assert api_index._engagement_message_count(75) == 5
    assert api_index._engagement_message_count(150) == 5
    assert api_index._engagement_message_count("bad") == 3
    assert api_index._engagement_message_count(20, candidate_rank=1, candidate_pool_size=10) == 5
    assert api_index._engagement_message_count(20, candidate_rank=3, candidate_pool_size=10) == 5
    assert api_index._engagement_message_count(90, candidate_rank=4, candidate_pool_size=10) == 4
    assert api_index._engagement_message_count(90, candidate_rank=8, candidate_pool_size=10) == 3
    print("✓ Engagement message count tests passed")

def test_engagement_chat_normalization():
    print("Testing engagement chat normalization...")
    candidate = _sample_candidate(match_score=85)
    jd = _sample_jd()
    long_message = " ".join(["This is a long realistic message"] * 20)
    raw_chat = [
        {"sender": "AI Recruiter", "message": long_message},
        {"sender": "Candidate", "message": "Thanks, I can take a look."},
        {"sender": "ALIGNA", "message": "Great, I can send the brief."},
        {"sender": "Ava Chen", "message": "Please share compensation and setup."},
        {"sender": "Recruiter", "message": "Will do."},
        {"sender": "ALIGNA", "message": "This extra message should be trimmed."},
    ]

    logs = api_index._normalize_chat_logs(raw_chat, candidate, jd, 5)
    assert len(logs) == 5
    assert logs[0].sender == "ALIGNA"
    assert logs[1].sender == candidate.name
    assert logs[2].sender == "ALIGNA"
    assert logs[3].sender == candidate.name
    assert logs[4].sender == "ALIGNA"
    assert len(logs[0].message) <= 220

    mislabeled_chat = [
        {"sender": candidate.name, "message": "Hi Ava, I have a frontend role that may fit."},
        {"sender": candidate.name, "message": "Thanks, I can take a quick look."},
        {"sender": candidate.name, "message": "Great, I will send a short brief."},
    ]
    logs = api_index._normalize_chat_logs(mislabeled_chat, candidate, jd, 3)
    assert [log.sender for log in logs] == ["ALIGNA", candidate.name, "ALIGNA"]

    low_score_logs = api_index._build_synthetic_chat_logs(candidate, jd, api_index._engagement_message_count(40))
    high_score_logs = api_index._build_synthetic_chat_logs(candidate, jd, api_index._engagement_message_count(85))
    assert len(low_score_logs) == 3
    assert len(high_score_logs) == 5
    print("✓ Engagement chat normalization tests passed")

def test_interest_explanation_normalization():
    print("Testing interest explanation normalization...")
    candidate = _sample_candidate(match_score=85)
    jd = _sample_jd()
    long_factor = " ".join(["Candidate asked specific follow-up questions"] * 12)

    reason, factors = api_index._normalize_interest_explanation(
        "",
        [],
        candidate,
        jd,
        interest_score=75,
        match_score=85,
    )
    assert reason
    assert len(factors) >= 2

    reason, factors = api_index._normalize_interest_explanation(
        "Strong interest because the candidate is open and engaged.",
        [long_factor, {"detail": "Work setup aligns."}, ""],
        candidate,
        jd,
        interest_score=80,
        match_score=85,
    )
    assert "Strong interest" in reason
    assert len(factors) == 2
    assert len(factors[0]) <= 160

    reason, factors = api_index._normalize_interest_explanation(
        "Basic match and remote preference",
        ["remote preference match", "basic role match"],
        candidate,
        jd,
        interest_score=60,
        match_score=45,
    )
    assert "Basic match" not in reason
    assert all("basic" not in factor.lower() for factor in factors)
    print("✓ Interest explanation normalization tests passed")

async def test_missing_optional_criteria_are_not_scored():
    print("Testing missing optional criteria are not scored...")

    candidate = _sample_candidate(match_score=0).model_dump()

    async def fake_load_candidates():
        return [candidate], "test"

    async def fake_generate_gemini_text(*args, **kwargs):
        raise RuntimeError("skip explainability in scoring regression test")

    original_load_candidates = api_index._load_candidates
    original_generate_gemini_text = api_index._generate_gemini_text
    api_index._load_candidates = fake_load_candidates
    api_index._generate_gemini_text = fake_generate_gemini_text

    try:
        jd = _sample_jd()

        response = await api_index.match_candidates(api_index.MatchRequest(jd_data=jd))
        matched = response.candidates[0]
        criteria = {criterion.key: criterion for criterion in matched.score_breakdown.criteria}

        assert matched.match_score == 100
        assert matched.score_breakdown.base_score == 100
        assert matched.score_breakdown.penalties == []
        assert criteria["must"].evaluated
        assert criteria["experience"].evaluated
        assert criteria["role"].evaluated
        assert not criteria["good"].evaluated
        assert not criteria["location"].evaluated
        assert not criteria["work_mode"].evaluated
    finally:
        api_index._load_candidates = original_load_candidates
        api_index._generate_gemini_text = original_generate_gemini_text

async def test_location_mismatch_is_weighted_not_penalized():
    print("Testing location mismatch uses weight, not penalty...")

    candidate = _sample_candidate(match_score=0).model_dump()

    async def fake_load_candidates():
        return [candidate], "test"

    async def fake_generate_gemini_text(*args, **kwargs):
        raise RuntimeError("skip explainability in scoring regression test")

    original_load_candidates = api_index._load_candidates
    original_generate_gemini_text = api_index._generate_gemini_text
    api_index._load_candidates = fake_load_candidates
    api_index._generate_gemini_text = fake_generate_gemini_text

    try:
        jd = _sample_jd()
        jd.location = "London, UK"

        response = await api_index.match_candidates(api_index.MatchRequest(jd_data=jd))
        matched = response.candidates[0]
        criteria = {criterion.key: criterion for criterion in matched.score_breakdown.criteria}

        assert matched.match_score < 100
        assert matched.score_breakdown.penalty_multiplier == 1.0
        assert matched.score_breakdown.penalties == []
        assert criteria["location"].evaluated
        assert criteria["location"].achieved_percent == 0
    finally:
        api_index._load_candidates = original_load_candidates
        api_index._generate_gemini_text = original_generate_gemini_text

if __name__ == "__main__":
    try:
        test_clamping()
        test_skill_matching()
        test_location_alignment()
        test_work_mode_alignment()
        test_engagement_message_count()
        test_engagement_chat_normalization()
        test_interest_explanation_normalization()
        asyncio.run(test_missing_optional_criteria_are_not_scored())
        asyncio.run(test_location_mismatch_is_weighted_not_penalized())
        print("\nAll backend logic tests passed successfully!")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")
        sys.exit(1)
