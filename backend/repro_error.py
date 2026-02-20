import requests
from auth.jwt_handler import create_access_token
from db.models import UserRole

# Generate token for teacher (ID 2)
token = create_access_token(user_id=2, email="gowtham@school.edu.in", role="teacher")

url = "http://localhost:8000/api/teacher/stats"
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Body: {response.text}")
