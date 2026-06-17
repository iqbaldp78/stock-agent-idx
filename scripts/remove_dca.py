from db import SessionLocal
from db.models import DcaStrategy

def remove_bbtn():
    db = SessionLocal()
    try:
        deleted = db.query(DcaStrategy).filter(DcaStrategy.ticker == "BBTN").delete()
        db.commit()
        print(f"Removed {deleted} DCA strategies for BBTN.")
    finally:
        db.close()

if __name__ == "__main__":
    remove_bbtn()
