import jwt, datetime
SECRET_KEY = "hamboo_secret_key"
ALGORITHM = "HS256"
payload = {
    "sub": "testkopong",
    "user_id": 10,
    "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=1440)
}
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(token)
