#!/usr/bin/env python3
"""
Validasi malam untuk log prediksi ML (ml_prediction_log).

Dua perbaikan penting dibanding versi sebelumnya:

1. LABEL. Dulu benar/salah dinilai dengan `actual_return > 0`, padahal model
   dilatih untuk memprediksi kenaikan di ATAS threshold (1d +0.6%, 3d +1.8%,
   5d +2.5%, 7d +3.0%). Akibatnya sinyal 5d yang naik +0.3% dihitung WIN
   walaupun bagi model itu label 0, dan win rate yang dilaporkan tidak pernah
   mengukur hal yang sama dengan yang dilatih. Sekarang threshold dibaca dari
   data.ml_features.TARGET_THRESHOLDS — sumber yang sama dengan training.

2. WINDOW. Dulu horizon 3d/5d/7d memakai `raw.index > trade_date` lalu
   iloc[days-1], sementara base close diambil dari hari sebelum trade_date —
   jadi 3d sebenarnya diukur sepanjang 4 hari bursa, 5d jadi 6, 7d jadi 8.
   Sekarang semua horizon memakai window yang sama dengan shift() di training:
   base = close hari bursa terakhir SEBELUM trade_date, target = close pada
   hari bursa ke-N dihitung dari trade_date (inklusif).
"""
import sys, os, argparse, logging
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import SessionLocal
from db.models import MlPredictionLog
from scripts.train_day1_model import get_universe_tickers, fetch_ohlcv
from models.multiday_predictor import MultiDayPredictor
from data.ml_features import TARGET_THRESHOLDS, TARGET_HORIZON_DAYS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_db_session():
    return SessionLocal()


def resolve_window(raw, trade_date, horizon):
    """
    Kembalikan (base_close, target_close) untuk satu prediksi, atau None kalau
    horizon belum matang (bar target belum ada).

    base_close   = close hari bursa terakhir STRICTLY SEBELUM trade_date.
                   Ini baris fitur yang dipakai saat prediksi dibuat.
    target_close = close hari bursa ke-N dihitung dari trade_date inklusif,
                   yaitu base_index + N — persis sama dengan Close.shift(-N)
                   di prepare_training_data().
    """
    days = TARGET_HORIZON_DAYS.get(horizon)
    if days is None:
        return None

    key = str(trade_date)
    past = raw.loc[raw.index < key]
    future = raw.loc[raw.index >= key]
    if past.empty or len(future) < days:
        return None

    base_close = float(past["Close"].iloc[-1])
    target_close = float(future["Close"].iloc[days - 1])
    if base_close <= 0:
        return None
    return base_close, target_close


def was_buy_signal(log, buy_threshold):
    """
    Keputusan BUY yang BENAR-BENAR diambil saat prediksi dibuat.

    Sumber utamanya kolom `predicted_direction`, karena itu yang tercatat pada
    waktu prediksi dengan threshold yang berlaku SAAT ITU. Menurunkan ulang
    keputusan dari `predictor.thresholds` (dibaca fresh dari disk) bikin verdict
    historis diam-diam berubah setiap kali model diretrain: threshold bergeser,
    row yang dulu BUY jadi non-BUY, dan aturan penilaian ikut terbalik —
    sinyal BUY yang rugi malah ke-mark benar. Log-nya berhenti jadi audit trail.

    `buy_threshold` dipakai hanya sebagai fallback untuk log lama yang
    predicted_direction-nya NULL.
    """
    if log.predicted_direction:
        return log.predicted_direction.upper() == "NAIK"
    pred_val = float(log.pred_return_pct) if log.pred_return_pct is not None else 0.0
    return pred_val >= buy_threshold


def score_log(log, raw, buy_threshold):
    """
    Hitung ulang actual_return / is_correct untuk satu log.
    Return True kalau log berhasil dinilai, False kalau di-skip.
    """
    window = resolve_window(raw, log.trade_date, log.horizon)
    if window is None:
        return False

    base_close, target_close = window
    actual_return = ((target_close - base_close) / base_close) * 100

    # Label yang PERSIS sama dengan training: naik di atas threshold horizon.
    target_pct = TARGET_THRESHOLDS[log.horizon] * 100
    label_up = actual_return > target_pct

    predicted_buy = was_buy_signal(log, buy_threshold)

    log.actual_close_price = target_close
    log.actual_return_pct = actual_return
    log.is_correct = bool(label_up) if predicted_buy else bool(not label_up)
    log.validated_at = datetime.now()
    return True


def main():
    ap = argparse.ArgumentParser(description="Validasi log prediksi ML.")
    ap.add_argument("--revalidate-all", action="store_true",
                    help="Nilai ulang SEMUA log (termasuk yang sudah tervalidasi), "
                         "bukan cuma yang actual_close_price masih NULL.")
    ap.add_argument("--since", type=str, default=None,
                    help="Batasi ke trade_date >= YYYY-MM-DD.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Hitung dan laporkan perubahan tanpa commit ke DB.")
    args = ap.parse_args()

    session = get_db_session()
    q = session.query(MlPredictionLog)
    if not args.revalidate_all:
        q = q.filter(MlPredictionLog.actual_close_price == None)  # noqa: E711
    if args.since:
        q = q.filter(MlPredictionLog.trade_date >= date.fromisoformat(args.since))
    targets = q.all()

    mode = "REVALIDATE-ALL" if args.revalidate_all else "pending saja"
    logging.info(f"Mulai Validasi ML ({mode}). {len(targets)} log jadi kandidat."
                 + (" [DRY RUN]" if args.dry_run else ""))

    by_ticker = {}
    for log in targets:
        by_ticker.setdefault(log.ticker, []).append(log)

    scored = 0
    skipped = 0
    flipped = 0
    for ticker, logs in by_ticker.items():
        try:
            raw = fetch_ohlcv(ticker, "6mo")
            if raw.empty:
                logging.warning(f"{ticker}: OHLCV kosong, {len(logs)} log di-skip.")
                skipped += len(logs)
                continue

            predictor = MultiDayPredictor(ticker=ticker)

            for log in logs:
                before = log.is_correct
                buy_threshold = predictor.thresholds.get(log.horizon, 0.55)
                if score_log(log, raw, buy_threshold):
                    scored += 1
                    if before is not None and before != log.is_correct:
                        flipped += 1
                else:
                    skipped += 1
        except Exception as e:
            logging.error(f"Error {ticker}: {e}")
            skipped += len(logs)

    if args.dry_run:
        session.rollback()
        logging.info(f"[DRY RUN] {scored} log akan dinilai, {skipped} di-skip "
                     f"(belum matang / tanpa data), {flipped} berubah hasilnya. Tidak ada commit.")
    else:
        session.commit()
        logging.info(f"Selesai Validasi ML. {scored} log dinilai, {skipped} di-skip "
                     f"(belum matang / tanpa data), {flipped} berubah hasilnya.")
    session.close()


if __name__ == "__main__":
    main()
