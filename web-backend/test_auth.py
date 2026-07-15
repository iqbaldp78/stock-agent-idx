import os
from sqlalchemy import text
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta

# Create a small script to test auth tokens and user setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "hamboo_super_secret_key_for_testing"
ALGORITHM = "HS256"

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=1440)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

if __name__ == "__main__":
    hashed = get_password_hash("password123")
    print(f"Hashed: {hashed}")
    token = create_access_token({"sub": "admin", "user_id": 1, "tier": "pro"})
    print(f"Token: {token}")
