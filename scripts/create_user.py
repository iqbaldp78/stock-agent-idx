import argparse
import sys
import os

# Ensure we can import from the root directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth import hash_password
from ui.app import get_db_conn

def create_user(username, password):
    hashed_pw = hash_password(password)
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, is_active) VALUES (%s, %s, TRUE)",
            (username, hashed_pw)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"Successfully created user: {username}")
    except Exception as e:
        print(f"Failed to create user. Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new user for Stock Agent IDX")
    parser.add_argument("username", help="The username for the new account")
    parser.add_argument("password", help="The password for the new account")
    
    args = parser.parse_args()
    create_user(args.username, args.password)
