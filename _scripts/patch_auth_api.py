from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "hamboo_super_secret_key_for_testing"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class AuthRequest(BaseModel):
    username: str
    password: str

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=1440)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Route code to append to main.py
route_code = """

# --- Auth Routes ---
from pydantic import BaseModel
class AuthRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/register")
def register_user(req: AuthRequest):
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        with engine.connect() as conn:
            with conn.begin():
                # Check if exists
                user = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": req.username}).fetchone()
                if user:
                    raise HTTPException(status_code=400, detail="Username already registered")
                
                hashed = pwd_context.hash(req.password)
                res = conn.execute(text("INSERT INTO users (username, password_hash, tier) VALUES (:u, :p, 'free') RETURNING id"), 
                                 {"u": req.username, "p": hashed})
                new_id = res.fetchone()[0]
                
                # Also create paper wallet for new user
                conn.execute(text("INSERT INTO paper_wallet (cash, total_topup, total_invested, total_pnl, user_id) VALUES (10000000, 10000000, 0, 0, :uid)"), {"uid": new_id})
                
        return {"status": "success", "message": "User registered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
def login_user(req: AuthRequest):
    try:
        from passlib.context import CryptContext
        import jwt
        from datetime import datetime, timedelta
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        with engine.connect() as conn:
            user = conn.execute(text("SELECT id, username, password_hash, tier FROM users WHERE username = :u"), {"u": req.username}).fetchone()
            
            if not user or not pwd_context.verify(req.password, user[2]):
                raise HTTPException(status_code=401, detail="Invalid username or password")
                
            # Create token
            expire = datetime.utcnow() + timedelta(minutes=1440)
            to_encode = {"sub": user[1], "user_id": user[0], "tier": user[3], "exp": expire}
            encoded_jwt = jwt.encode(to_encode, "hamboo_super_secret_key_for_testing", algorithm="HS256")
            
            return {"access_token": encoded_jwt, "token_type": "bearer", "tier": user[3], "user_id": user[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/me")
def get_me(token: str = ""):
    import jwt
    try:
        if not token:
            raise HTTPException(status_code=401)
        payload = jwt.decode(token, "hamboo_super_secret_key_for_testing", algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

"""

with open("web-backend/main.py", "a") as f:
    f.write(route_code)
