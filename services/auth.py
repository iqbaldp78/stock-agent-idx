import bcrypt
import logging
from sqlalchemy.orm import sessionmaker
from db.models import User
import psycopg2
import psycopg2.extras
import os

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def authenticate_user(username, password, get_db_conn_func):
    """
    Authenticates a user against the database.
    Returns the user dict if successful, None otherwise.
    """
    try:
        conn = get_db_conn_func()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s AND is_active = TRUE", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and verify_password(password, user['password_hash']):
            return user
        return None
    except Exception as e:
        logger.error(f"DB authentication error: {e}")
        return None
