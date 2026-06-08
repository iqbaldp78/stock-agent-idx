"""
Validasi bahwa schema signals sudah benar dan bisa insert data dengan target_3.
"""
from datetime import date
from sqlalchemy import text
from db import SessionLocal
from db.models import Signal
import json

def validate_signals_schema():
    """Validasi schema signals dan coba insert sample data."""
    db = SessionLocal()
    try:
        # 1. Cek apakah tabel signals ada dan kolom target_3 exist
        result = db.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='signals' AND column_name='target_3'
        """))
        
        if not result.fetchone():
            print("❌ ERROR: Column 'target_3' tidak ditemukan di tabel signals")
            return False
        
        print("✓ Column 'target_3' ditemukan")
        
        # 2. Cek semua kolom yang diperlukan
        required_columns = [
            'target_1', 'target_2', 'target_3', 
            'tp_position_sizing', 'risk_reward_tp1', 
            'risk_reward_tp2', 'risk_reward_tp3'
        ]
        
        for col in required_columns:
            result = db.execute(text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='signals' AND column_name='{col}'
            """))
            if result.fetchone():
                print(f"✓ Column '{col}' ditemukan")
            else:
                print(f"❌ ERROR: Column '{col}' tidak ditemukan")
                return False
        
        # 3. Coba insert sample data
        print("\n--- Testing INSERT dengan sample data ---")
        test_signal = Signal(
            run_date=date.today(),
            ticker="TEST",
            rank=1,
            signal="BUY",
            entry_low=1000.00,
            entry_high=1100.00,
            max_entry=1050.00,
            target_1=1200.00,
            target_2=1300.00,
            target_3=1400.00,
            stop_loss=950.00,
            risk_reward=1.5,
            conviction="HIGH",
            thesis="Test thesis",
            entry_reasoning="Test entry reasoning",
            bandar_avg_7d=1050.00,
            bandar_avg_1m=1040.00,
            broker_utama="Test Broker",
            time_horizon="4-6 minggu",
            weight_mode="test",
            composite_score=6.5,
            price_prediction=json.dumps({"test": "data"}),
            tp_position_sizing=json.dumps({
                "tp1_size": 0.3,
                "tp2_size": 0.4,
                "tp3_size": 0.3
            }),
            risk_reward_tp1="1.5",
            risk_reward_tp2="2.0",
            risk_reward_tp3="2.5"
        )
        
        db.add(test_signal)
        db.commit()
        
        print("✓ Sample data berhasil diinsert dengan target_3")
        
        # 4. Verify data yang diinsert
        result = db.query(Signal).filter(Signal.ticker == "TEST").first()
        if result and result.target_3 == 1400.00:
            print("✓ Data target_3 verified: 1400.00")
        else:
            print("❌ ERROR: Data target_3 tidak tersimpan dengan benar")
            return False
        
        # 5. Cleanup
        db.delete(result)
        db.commit()
        print("✓ Test data dibersihkan")
        
        print("\n✅ VALIDASI BERHASIL - Schema signals siap untuk digunakan!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = validate_signals_schema()
    exit(0 if success else 1)
