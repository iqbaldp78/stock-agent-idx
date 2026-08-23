#!/bin/bash
# Rantai analisis ML tanpa pengawasan. Dijalankan detached (nohup) supaya tetap
# hidup setelah VSCode / sesi Claude ditutup — tidak ada bagian yang butuh Claude.
# Tiap langkah dicatat dan TIDAK menghentikan rantai kalau gagal, supaya laporan
# akhir tetap terbit dari apa pun yang berhasil.
cd /home/hamboo/my-product/stock-agent-idx || exit 1
LOG=scratch/chain.log
say(){ echo "[$(date '+%F %T')] $*" >> "$LOG"; }
run(){ say "MULAI: $*"; if "$@" >> "$LOG" 2>&1; then say "OK   : $1 $2"; else say "GAGAL: $1 $2 (rantai lanjut)"; fi; }
D="docker exec -w /app stock_app python"

: > "$LOG"
say "=== rantai dimulai ==="

say "menunggu validasi walk-forward yang sedang jalan..."
while pgrep -f "train_multiday_model.py --all --period 5y --walk-forward" > /dev/null; do sleep 60; done
say "validasi walk-forward selesai"

run $D scripts/feature_ic_study.py --all --period 5y \
      --out scratch/feature_ic.json --dump-panel scratch/panel.parquet

run $D scripts/xs_quintile_study.py --panel scratch/panel.parquet \
      --out scratch/xs_quintile.json

run $D scripts/cron_ml_validate.py
run $D scripts/ml_scorecard.py --days 14 \
      --out scratch/ml_scorecard.html --json scratch/ml_scorecard.json

run $D scripts/build_ml_report.py --out scratch/REPORT.md

say "=== rantai selesai ==="
touch scratch/CHAIN_DONE
