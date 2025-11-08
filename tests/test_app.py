"""
Tests for the Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name in activities:
        if name in original_activities:
            activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to the static index page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that GET /activities returns 200 OK"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that GET /activities returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_has_expected_activities(self, client):
        """Test that the response includes expected activities"""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = [
            "Chess Club", "Programming Class", "Gym Class", 
            "Basketball Team", "Swimming Club", "Art Club",
            "Drama Club", "Debate Team", "Math Club"
        ]
        
        for activity in expected_activities:
            assert activity in data
    
    def test_activity_has_required_fields(self, client):
        """Test that each activity has all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in data.items():
            for field in required_fields:
                assert field in activity_data, f"{activity_name} missing {field}"
    
    def test_participants_is_list(self, client):
        """Test that participants field is a list"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_data["participants"], list)


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup to an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant to the activity"""
        email = "teststudent@mergington.edu"
        
        # Sign up
        client.post(f"/activities/Math%20Club/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Math Club"]["participants"]
    
    def test_signup_nonexistent_activity_returns_404(self, client):
        """Test that signing up for a nonexistent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_returns_400(self, client):
        """Test that signing up twice returns 400 error"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Drama%20Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Drama%20Club/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_full_activity_returns_400(self, client):
        """Test that signing up for a full activity returns 400"""
        # Fill up Chess Club (max 12 participants)
        for i in range(12):
            response = client.post(f"/activities/Chess%20Club/signup?email=student{i}@mergington.edu")
            if i < 10:  # First 10 should succeed (2 already exist)
                assert response.status_code == 200
        
        # Next signup should fail
        response = client.post("/activities/Chess%20Club/signup?email=overflow@mergington.edu")
        assert response.status_code == 400
        data = response.json()
        assert "full" in data["detail"].lower()
    
    def test_signup_requires_email_parameter(self, client):
        """Test that signup requires an email parameter"""
        response = client.post("/activities/Art%20Club/signup")
        assert response.status_code == 422  # Validation error


class TestUnregisterEndpoint:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        # First sign up
        email = "testunregister@mergington.edu"
        client.post(f"/activities/Swimming%20Club/signup?email={email}")
        
        # Then unregister
        response = client.delete(f"/activities/Swimming%20Club/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
    
    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "removetest@mergington.edu"
        
        # Sign up
        client.post(f"/activities/Debate%20Team/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Debate Team"]["participants"]
        
        # Unregister
        client.delete(f"/activities/Debate%20Team/unregister?email={email}")
        
        # Verify participant was removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Debate Team"]["participants"]
    
    def test_unregister_nonexistent_activity_returns_404(self, client):
        """Test that unregistering from a nonexistent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_unregister_not_signed_up_returns_404(self, client):
        """Test that unregistering when not signed up returns 404"""
        response = client.delete(
            "/activities/Basketball%20Team/unregister?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # Michael is already signed up for Chess Club
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify removal
        response = client.get("/activities")
        data = response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]
    
    def test_unregister_requires_email_parameter(self, client):
        """Test that unregister requires an email parameter"""
        response = client.delete("/activities/Art%20Club/unregister")
        assert response.status_code == 422  # Validation error


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_signup_unregister_workflow(self, client):
        """Test a complete workflow: signup, verify, unregister, verify"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Get initial state
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity.replace(' ', '%20')}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        data = response.json()
        assert email in data[activity]["participants"]
        assert len(data[activity]["participants"]) == initial_count + 1
        
        # Unregister
        response = client.delete(f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify unregister
        response = client.get("/activities")
        data = response.json()
        assert email not in data[activity]["participants"]
        assert len(data[activity]["participants"]) == initial_count
    
    def test_multiple_students_signup(self, client):
        """Test multiple students signing up for the same activity"""
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for student in students:
            response = client.post(f"/activities/Gym%20Class/signup?email={student}")
            assert response.status_code == 200
        
        # Verify all students are signed up
        response = client.get("/activities")
        data = response.json()
        for student in students:
            assert student in data["Gym Class"]["participants"]
