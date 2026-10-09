import pytest
from fastapi.testclient import TestClient
from app.main import app
from seed.seed import run_seed

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    run_seed()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_unauthenticated_access_redirects_to_login():
    response = client.get("/passport", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    response = client.get("/post/new", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_stale_session_cookie_redirects_to_login():
    client.cookies.set("urfeast_user_id", "999999")
    response = client.get("/passport", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

def test_feed_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "URFeast" in response.text
    assert "Community Food & Label Intelligence" in response.text


def test_demo_sample_assets_exist():
    for path in ["/uploads/sample_biscuit.jpg", "/uploads/sample_thali.jpg"]:
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")


def test_language_selection_is_english_only():
    client.post("/login", data={"user_id": 1})
    response = client.get("/passport")
    html = response.text

    assert 'value="en"' in html
    assert 'value="hi"' not in html
    assert 'value="kn"' not in html
    assert "Hindi" not in html
    assert "Kannada" not in html


def test_passport_save():
    client.post("/login", data={"user_id": 1})
    res = client.post("/passport", data={
        "diet_type": "veg",
        "allergies": ["peanuts"],
        "avoid_list_str": "palm oil, high sugar",
        "goals": ["low sugar"],
        "language": "en",
        "conditions_note": "Demo note",
        "budget_note": "Student budget",
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "Save Diet Passport" in res.text

def test_demo_login():
    response = client.get("/login")
    assert response.status_code == 200
    assert "Aarav Sharma" in response.text
    assert "Dr. Nisha Rao" in response.text

    # Switch login to Aarav
    login_res = client.post("/login", data={"user_id": 1}, follow_redirects=False)
    assert login_res.status_code == 303
    assert "urfeast_user_id=1" in login_res.headers.get("set-cookie", "")

def test_post_creation_and_analysis():
    # Login as Aarav
    client.post("/login", data={"user_id": 1})

    res = client.post("/post/new", data={
        "question_text": "Is this biscuit okay for my afternoon snack? Does it contain high sugar or palm oil?",
        "image_kind": "label",
        "community_id": 2
    }, follow_redirects=True)

    assert res.status_code == 200
    assert "Gemma 4 Perception & Analysis" in res.text
    assert "Evidence-Tagged Observations" in res.text

def test_unsafe_peer_reply_audit():
    # Post #1 is Aarav's post (Peanut allergy)
    # Login as Riya (peer)
    client.post("/login", data={"user_id": 4})

    reply_res = client.post("/post/1/reply", data={
        "body": "Add peanut chutney on the side, it tastes great with tea!"
    })
    
    assert reply_res.status_code == 200
    assert "Conflicts with poster's Passport" in reply_res.text or "peanut" in reply_res.text
    assert "unsafe" in reply_res.text or "Warning" in reply_res.text

def test_safe_dietitian_reply_and_approval():
    # Login as Dr. Nisha Rao (dietitian)
    client.post("/login", data={"user_id": 6})

    reply_res = client.post("/post/1/reply", data={
        "body": "No peanuts listed. Limit to 2 biscuits max to stay under your low-sugar goal limit."
    })
    assert reply_res.status_code == 200
    assert "Verified Dietitian" in reply_res.text

    # Approve plan
    appr_res = client.post("/post/1/approve", follow_redirects=True)
    assert appr_res.status_code == 200
    assert "Dietitian Approved Plan" in appr_res.text

def test_final_plan_synthesis():
    plan_res = client.post("/post/1/final_plan")
    assert plan_res.status_code == 200
    assert "Final Synthesized Action Plan" in plan_res.text
    # Ensure unsafe peanut chutney is NOT included in final plan
    assert "peanut chutney" not in plan_res.text.lower()

def test_label_library_search():
    res = client.get("/library?q=NutriChoice")
    assert res.status_code == 200
    assert "NutriChoice Digestive Biscuit" in res.text

def test_dietitian_queue():
    # Login as Dr. Nisha
    client.post("/login", data={"user_id": 6})
    res = client.get("/dietitian/queue")
    assert res.status_code == 200
    assert "Triaged Clinical Posts" in res.text

def test_admin_verification():
    # Login as Admin
    client.post("/login", data={"user_id": 8})
    res = client.get("/admin/verify")
    assert res.status_code == 200
    assert "Dietitian Credentials Verification" in res.text
