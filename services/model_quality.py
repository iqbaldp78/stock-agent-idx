"""
Kualitas model ML seperti apa adanya, dibaca dari metadata hasil training.

Satu sumber untuk semua konsumen (API, Streamlit, frontend) supaya angka yang
ditampilkan di sebelah sinyal tidak pernah berbeda antar halaman.

Metrik yang dipakai: buy precision dikurangi base rate — dari sinyal yang benar-benar
bilang BELI, berapa persen kena target, dibanding berapa persen SELURUH saham kena
target pada periode yang sama. Selisih itu (edge) adalah satu-satunya angka yang
menyatakan apakah model menambahkan sesuatu di atas "beli acak".

Akurasi keseluruhan sengaja TIDAK dipakai: mayoritas prediksi berisi TURUN dan
"benar kalau tidak naik" mudah terpenuhi, jadi angkanya tinggi tanpa model perlu
punya kemampuan apa pun.

PENTING: kalau training dijalankan tanpa walk-forward, edge yang dilaporkan tidak
bisa dipercaya. Single holdout split memotong ekor data tanpa purge gap, sehingga
label horizon 3d/5d/7d di batas blok bocor ke train dan edge-nya jadi artefak split.
Dalam kondisi itu verdict-nya "unmeasured", bukan angkanya yang ditampilkan.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

DEFAULT_META_PATH = "models/checkpoints/lgbm_multiday_meta.json"
HORIZONS = ("1d", "3d", "5d", "7d")

# Ambang edge (poin persen) untuk melabeli hasil. Sengaja konservatif: sampel per
# horizon di log live hanya 54-152 sinyal, jadi interval kepercayaan 95%-nya ±8
# sampai ±12pp. Edge di bawah 2pp tidak bisa dibedakan dari nol.
EDGE_MARGINAL = 2.0

_cache = {"mtime": None, "path": None, "data": None}


def _verdict(edge, lift, walk_forward):
    if not walk_forward:
        return ("unmeasured", "Belum terukur andal",
                "Training terakhir memakai single holdout split tanpa purge gap, "
                "sehingga edge yang dilaporkannya adalah artefak split. Jalankan "
                "ulang training dengan walk-forward untuk angka yang bisa dipakai.")
    if edge is None:
        return ("unmeasured", "Belum terukur andal", "Metadata training tidak lengkap.")
    if edge <= 0:
        return ("no_edge", "Tanpa edge",
                f"Sinyal BELI model justru {abs(edge):.1f} poin persen DI BAWAH "
                f"peluang dasar pasar (lift {lift:.2f} bila <1 berarti nol skill). "
                "Jangan dipakai sebagai dasar keputusan beli.")
    if edge < EDGE_MARGINAL:
        return ("marginal", "Dalam derau",
                f"Edge +{edge:.1f} poin persen, lebih kecil dari ketidakpastian "
                "sampelnya sendiri, jadi belum bisa dibedakan dari nol.")
    return ("edge", "Ada edge terukur",
            f"Sinyal BELI model {edge:.1f} poin persen di atas peluang dasar pasar "
            f"(lift {lift:.2f}).")


def load_model_quality(meta_path=DEFAULT_META_PATH, use_cache=True):
    """
    Baca metadata training dan kembalikan ringkasan kualitas per horizon.
    Selalu mengembalikan dict — kalau file tidak ada, available=False.
    """
    try:
        mtime = os.path.getmtime(meta_path)
    except OSError:
        return {"available": False, "reason": f"metadata tidak ditemukan: {meta_path}",
                "horizons": {}}

    if use_cache and _cache["data"] is not None \
            and _cache["mtime"] == mtime and _cache["path"] == meta_path:
        return _cache["data"]

    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        logger.warning("Gagal membaca %s: %s", meta_path, e)
        return {"available": False, "reason": str(e), "horizons": {}}

    cfg = meta.get("config", {}) or {}
    walk_forward = bool(cfg.get("walk_forward", False))
    metrics = meta.get("holdout_metrics_macro_avg", {}) or {}

    horizons = {}
    for hz in HORIZONS:
        m = metrics.get(hz) or {}
        prec = m.get("buy_precision")
        base = m.get("base_rate")
        lift = m.get("lift")
        edge = (prec - base) if (prec is not None and base is not None) else None
        verdict, label, message = _verdict(edge, lift if lift is not None else 0.0,
                                          walk_forward)
        horizons[hz] = {
            "buy_precision": prec,
            "base_rate": base,
            "edge_pp": round(edge, 2) if edge is not None else None,
            "lift": lift,
            "n_usable": m.get("n_usable"),
            "n_degenerate": m.get("n_degenerate"),
            "test_rows": m.get("test_rows"),
            "verdict": verdict,
            "label": label,
            "message": message,
        }

    data = {
        "available": True,
        "run_date": meta.get("run_date"),
        "walk_forward": walk_forward,
        "trustworthy": walk_forward,
        "period": cfg.get("period"),
        "n_folds": cfg.get("n_folds"),
        "tickers_trained": (meta.get("rows") or {}).get("tickers_trained"),
        "horizons": horizons,
    }
    _cache.update({"mtime": mtime, "path": meta_path, "data": data})
    return data


def horizon_quality(horizon, meta_path=DEFAULT_META_PATH):
    """Ringkasan untuk satu horizon ('1d'/'1D'/...). Kembalikan None kalau tidak ada."""
    q = load_model_quality(meta_path)
    if not q.get("available"):
        return None
    return q["horizons"].get(str(horizon).lower())
