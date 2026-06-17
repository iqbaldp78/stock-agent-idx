from sqlalchemy import text
from db import SessionLocal

def reset_database():
    db = SessionLocal()
    try:
        # Menghapus data dari tabel operasional/development
        # Harus menghapus performance & dca_transactions terlebih dahulu karena Foreign Key
        db.execute(text("DELETE FROM performance;"))
        db.execute(text("DELETE FROM dca_transactions;"))
        db.execute(text("DELETE FROM dca_strategy;"))
        db.execute(text("DELETE FROM signals;"))
        db.execute(text("DELETE FROM agent_scores;"))
        db.execute(text("DELETE FROM debate_logs;"))
        
        db.commit()
        print("✅ Berhasil mereset data operasional dan development.")
        print("✅ Portfolio Holdings & Raw Cache tetap aman.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error saat mereset database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_database()
