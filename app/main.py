import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import httpx
import logging
from app.utils import is_valid_email

# Logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Redis connection
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

app = FastAPI()

class UserBio(BaseModel):
    name: str
    email: str
    age: int
    gender: str


@app.post("/api/user")
async def handle_user(bio: UserBio):
    logging.info(f"Received data: {bio}")

    if not is_valid_email(bio.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Store in Redis safely
    try:
        r.lpush("recent_users", bio.json())
        r.ltrim("recent_users", 0, 9)
    except Exception as e:
        logging.warning(f"Redis not available: {e}")

    # Forward to backend service
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{BACKEND_URL}/api/save", json=bio.dict())
            if res.status_code == 201:
                return {"message": "Data processed and sent to DB"}, 200
            elif res.status_code == 400:
                backend_msg = res.json().get("detail", "Bad Request")
                return {"message": backend_msg, "success": False}
            else:
                raise HTTPException(status_code=500, detail="Unexpected backend error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recent")
def get_recent():
    recent_data = r.lrange("recent_users", 0, 4)
    decoded = [x.decode("utf-8") for x in recent_data]
    return {"recent": decoded}

@app.get("/api/users")
async def get_all_users():
    try:
        async with httpx.AsyncClient() as client:
            # call backend (service-b)
            res = await client.get(f"{BACKEND_URL}/api/users")
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail="Backend error")
            return res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# --------------------------------------------------------------------
# GET /api/users/{user_id} - fetch single user by ID (via backend)
# --------------------------------------------------------------------
@app.get("/api/users/{user_id}")
async def get_user_by_id(user_id: int):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{BACKEND_URL}/api/users/{user_id}")
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=res.text)
            return res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------
# GET /api/user-by-email?email=... - fetch single user by email (via backend)
# --------------------------------------------------------------------
@app.get("/api/user-by-email")
async def get_user_by_email(email: str):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{BACKEND_URL}/api/user-by-email", params={"email": email})
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=res.text)
            return res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "healthy", "service": "frontend"}