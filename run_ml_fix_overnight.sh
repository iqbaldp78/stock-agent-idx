#!/bin/bash
# run_ml_fix_overnight.sh
# Script untuk menjalankan semua proses dari ML_FIX_FASE_1_2.md di background

LOG_FILE="logs_ml_fix_overnight.txt"
echo "=========================================================" > $LOG_FILE
echo "Memulai proses ML_FIX_FASE_1_2.md pada $(date)" >> $LOG_FILE
echo "=========================================================" >> $LOG_FILE

echo "[Langkah 00] Backup Checkpoint..." >> $LOG_FILE
docker compose exec app bash -c '
  D=models/checkpoints_backup_$(date +%Y%m%d_%H%M%S)
  mkdir -p "$D" && cp -a models/checkpoints/. "$D"/
  echo "Backup: $D"
  ls "$D"/*.pkl 2>/dev/null | wc -l
' >> $LOG_FILE 2>&1

echo "[Langkah 01] Cek Fitur Bandarmologi..." >> $LOG_FILE
docker compose exec app python3 -c "
import json, glob
files = sorted(glob.glob('models/checkpoints/lgbm_*_1d_features.json'))
print('sidecar diperiksa:', len(files))
keys = ['day_foreign_net','foreign_net_7d','foreign_net_1m','foreign_flow_zscore']
missing = {k: 0 for k in keys}
for p in files:
    f = json.load(open(p))['selected_features']
    for k in keys:
        if k not in f: missing[k] += 1
for k, v in missing.items():
    print(f'{k:24} tidak dipakai di {v}/{len(files)} model')" >> $LOG_FILE 2>&1

echo "[Langkah 02] Parity Check..." >> $LOG_FILE
make check-feature-parity >> $LOG_FILE 2>&1

echo "[Langkah 03] Parity Check (Short Window)..." >> $LOG_FILE
make check-feature-parity-shortwindow >> $LOG_FILE 2>&1

echo "[Langkah 04] Update ML Metadata..." >> $LOG_FILE
make update-ml-metadata >> $LOG_FILE 2>&1
docker compose exec app python3 -c "
import json; m = json.load(open('models/checkpoints/lgbm_multiday_meta.json'))
print(f\"{'H':<4}{'acc':>8}{'baseline':>10}{'lift':>8}{'usable':>8}{'degen':>7}\")
for h, v in m['holdout_metrics_macro_avg'].items():
    print(f\"{h:<4}{v['accuracy']:>7.2f}%{v['majority_baseline']:>9.2f}%\"
          f\"{v['lift']:>8.3f}{v['n_usable']:>8}{v['n_degenerate']:>7}\")" >> $LOG_FILE 2>&1

echo "[Langkah 05] Retrain Full..." >> $LOG_FILE
docker compose exec app bash -c '
  python scripts/train_multiday_model.py --all --period max
' >> $LOG_FILE 2>&1

echo "=========================================================" >> $LOG_FILE
echo "Proses ML_FIX_FASE_1_2.md selesai pada $(date)" >> $LOG_FILE
echo "=========================================================" >> $LOG_FILE
