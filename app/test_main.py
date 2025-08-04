from fastapi import FastAPI
from fastapi.testclient import TestClient
from .main import app

app = FastAPI()

@app.get("/")
async def read_main():
    return {"message": "gik_backend is running"}

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "gik_backend is running"}
    

def test_create_post():
    response = client.post("/v1/gik-backend/community", json={
        "user_id": "test",
        "title": "Test",
        "content": "테스트",
    })
    assert response.status_code == 201
    assert response.json() == {"message": "Post created successfully"}
