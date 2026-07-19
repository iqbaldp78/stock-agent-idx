#!/usr/bin/env python3
"""
ML Multi-Day Accuracy Validator
Script khusus untuk mengekstrak dan memvalidasi log/metadata dari
hasil training multiday_model.py dan menyajikannya secara terstruktur
untuk keperluan dashboard.

Bisa dijalankan manual melalui CLI:
    python scripts/validate_ml_multiday.py
"""
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

def get_multiday_validation_result():
    meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models/checkpoints/lgbm_multiday_meta.json")
    if not os.path.exists(meta_path):
        return {"error": "Metadata file not found. Run train_multiday_model.py first."}
    
    try:
        with open(meta_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    res = get_multiday_validation_result()
    print(json.dumps(res, indent=2))
