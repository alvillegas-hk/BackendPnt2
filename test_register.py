from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test 1: Simple registration
print("=== Test 1: Simple Registration ===")
response = client.post("/auth/register", json={
    "nombre": "Test",
    "apellido": "User",
    "email": "test123@example.com",
    "password": "Test1234!"
})
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test 2: Second registration (same email should fail)
print("\n=== Test 2: Duplicate Email ===")
response2 = client.post("/auth/register", json={
    "nombre": "Test2",
    "apellido": "User2",
    "email": "test123@example.com",
    "password": "Test1234!"
})
print(f"Status: {response2.status_code}")
print(f"Response: {response2.json()}")
