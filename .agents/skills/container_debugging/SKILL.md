---
name: container_debugging
description: Panduan dan instruksi baku untuk melakukan debugging, eksekusi kode fitur, test, inspeksi database, dan pengecekan log SELALU di dalam Docker container (bukan di mesin host).
---

# Container Execution & Debugging Guidelines

Gunakan aturan dan panduan ini setiap kali melakukan debugging, eksekusi script/fitur Python, running test, inspeksi database, atau pengecekan log.

> [!IMPORTANT]
> **ATURAN MUTLAK**: Agen **DILARANG** menjalankan script Python, unit test (`pytest`), atau query database langsung di mesin host. SEMUA perintah eksekusi HARUS dijalankan di dalam Docker container yang sesuai!

---

## 1. Pemetaan Service / Container Target

Pilih service target berdasarkan lokasi file atau modul yang sedang ditangani:

| Komponen / Jalur File | Service Docker | Container Name | Perintah Utama |
| :--- | :--- | :--- | :--- |
| Core agents (`agents/`), Scripts (`scripts/`), Data (`data/`), Scheduler | `app` | `stock_app` | `docker compose exec -T app python ...` |
| Web Backend (`web-backend/`), API endpoints | `web_api` | `web_user_api` | `docker compose exec -T web_api python ...` |
| Web Frontend (`web-frontend/`) | `web_frontend` | `web_user_frontend` | `docker compose exec -T web_frontend npm ...` |
| Database SQL Main | `postgres` | `stock_postgres` | `docker compose exec -T postgres psql -U stockuser -d stockagent` |
| Database Vector | `vector_postgres` | `vector_postgres` | `docker compose exec -T vector_postgres psql -U vectoruser -d vectoragent` |

---

## 2. Prosedur Pengecekan Status & Auto-Start

Sebelum menjalankan perintah eksekusi di dalam container:

1. **Cek status container**:
   ```bash
   docker compose ps
   ```
2. **Jika container service belum berjalan / stopped**:
   Nyalakan service secara otomatis terlebih dahulu:
   ```bash
   docker compose up -d <service>
   ```

---

## 3. Format Perintah Eksekusi Standard

- **Non-Interactive (Default untuk subshell / automated script)**:
  ```bash
  docker compose exec -T <service> <command>
  ```
- **Fallback (Jika container stopped & tidak ingin dinyalakan permanen)**:
  ```bash
  docker compose run --rm <service> <command>
  ```

---

## 4. Contoh Eksekusi Debugging Populer

### A. Eksekusi Script Python / Testing Feature
```bash
# Menjalankan script Python di service app
docker compose exec -T app python scripts/backtest_ihsg_strategy.py

# Menjalankan unit test dengan pytest
docker compose exec -T app pytest tests/

# Menjalankan perintah inline Python
docker compose exec -T app python -c "import config; print(config)"
```

### B. Inspeksi Backend API (`web_api`)
```bash
# Running test di backend web
docker compose exec -T web_api pytest web-backend/

# Pengecekan skema DB / Alembic migration
docker compose exec -T web_api alembic current
```

### C. Query / Inspeksi Database
```bash
# Masuk ke psql prompt / execute query langsung
docker compose exec -T postgres psql -U stockuser -d stockagent -c "\dt"
```

### D. Pengecekan Log Container
```bash
# Melihat 100 baris log terakhir service app
docker compose logs --tail 100 app

# Live tailing log service web_api
docker compose logs -f --tail 50 web_api
```
