# Database Schema Migration Guide

## Problem yang Terjadi
Error: `column "target_3" of relation "signals" does not exist`

Penyebab: Model SQLAlchemy mendefinisikan kolom baru (`target_3`, `tp_position_sizing`, `risk_reward_tp1`, `risk_reward_tp2`, `risk_reward_tp3`) tetapi database schema belum diupdate dengan migration Alembic.

## Solusi yang Diterapkan

### 1. Menjalankan Migration
```bash
docker-compose exec -T app alembic upgrade head
```

Output yang sukses:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 4bbaa11f38cf, add tp columns
```

### 2. Validasi Schema
```bash
docker-compose exec -T app python validate_schema.py
```

Script ini akan:
- Cek keberadaan semua kolom yang diperlukan
- Test INSERT data dengan kolom baru
- Verify data tersimpan dengan benar
- Cleanup test data

## Cara Mencegah Error Serupa di Masa Depan

### Workflow yang Benar

#### 1. Ketika Menambah Kolom Baru ke Database:

**Step 1: Update Model (db/models.py)**
```python
class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True)
    # ... existing columns ...
    target_3 = Column(Numeric(12, 2))  # Kolom baru
```

**Step 2: Generate Migration**
```bash
docker-compose exec -T app alembic revision --autogenerate -m "add target_3 column"
```

**Step 3: Review Generated Migration**
- Cek file di `db/migrations/versions/`
- Pastikan `upgrade()` dan `downgrade()` benar

**Step 4: Apply Migration**
```bash
docker-compose exec -T app alembic upgrade head
```

**Step 5: Validasi**
```bash
docker-compose exec -T app python validate_schema.py
```

#### 2. Saat Deploy atau Restart Container:

Selalu pastikan migrations sudah dijalankan:
```bash
# Otomatis dalam startup script atau di Dockerfile
docker-compose exec -T app alembic upgrade head
```

### Checklist Sebelum Push Code

- [ ] Model (db/models.py) sudah update dengan kolom baru
- [ ] Migration file sudah di-generate dan di-review
- [ ] Migration sudah dijalankan di database lokal
- [ ] Validation script berhasil (✅ VALIDASI BERHASIL)
- [ ] Code sudah di-test untuk insert/update dengan kolom baru
- [ ] Git diff menunjukkan:
  - Perubahan di db/models.py
  - File migration baru di db/migrations/versions/

## Struktur Migration File

Typical migration untuk menambah kolom:

```python
def upgrade() -> None:
    op.add_column('signals', sa.Column('target_3', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('signals', sa.Column('tp_position_sizing', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade() -> None:
    op.drop_column('signals', 'tp_position_sizing')
    op.drop_column('signals', 'target_3')
```

## Troubleshooting

### Error: "column does not exist"
- Run: `docker-compose exec -T app alembic upgrade head`
- Check: `docker-compose exec -T postgres psql -U stockuser -d stockagent -c "\d signals"`

### Migration file tidak ter-generate otomatis
1. Pastikan model sudah di-save
2. Jalankan: `docker-compose exec -T app alembic revision --autogenerate -m "description"`
3. Review file yang di-generate

### Validation script gagal
1. Pastikan migration sudah dijalankan
2. Check database connection: `docker-compose ps`
3. Run: `validate_schema.py` untuk diagnostik detail

## File Penting

- `db/models.py` - SQLAlchemy model definitions
- `db/migrations/versions/` - Migration scripts
- `alembic.ini` - Alembic configuration
- `validate_schema.py` - Schema validation script
