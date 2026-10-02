"""
Satu-satunya sumber kebenaran untuk membaca sinyal ML dari ml_prediction_log.

Sejarah: kolom pred_return_pct era-lama berisi probabilitas mentah [0,1]
(salah nama), dan tiap konsumen menduplikasi sniff `<= 1.0 -> x100` plus
cutoff BUY hardcode-nya sendiri (55.0 / 0.54 / 0.60). Sejak migrasi
mlpredprob01 probabilitas punya rumah sendiri (pred_prob) dan keputusan BUY
dibaca dari predicted_direction yang ditulis dengan threshold per-ticker saat
prediksi dibuat — bukan diturunkan ulang belakangan.
"""

STRONG_BUY_FALLBACK_PROB = 0.60


def prob_from_log(row):
    """
    Probabilitas klasifier [0,1] dari satu baris ml_prediction_log.

    Prefer pred_prob; fallback ke pred_return_pct legacy dengan sniff `<= 1.0`
    (baris persen dinormalkan /100). Ini SATU-SATUNYA tempat sniff itu boleh
    hidup. Return None kalau dua-duanya kosong.
    """
    p = getattr(row, "pred_prob", None)
    if p is not None:
        return float(p)
    legacy = getattr(row, "pred_return_pct", None)
    if legacy is None:
        return None
    legacy = float(legacy)
    return legacy if legacy <= 1.0 else legacy / 100.0


def prob_pct(prob):
    """Probabilitas [0,1] -> persen untuk display; None dibiarkan None."""
    return None if prob is None else float(prob) * 100.0


def buy_label(predicted_direction, prob=None, buy_threshold=None):
    """
    Label sinyal dari satu baris log. BUY hanya kalau predicted_direction
    tersimpan == "NAIK" — konsumen tidak menurunkan ulang keputusan dengan
    cutoff-nya sendiri. STRONG BUY memakai aturan yang sama dengan
    MultiDayPredictor.get_signal(): prob >= threshold*1.10; kalau threshold
    per-ticker tidak tersedia, fallback prob >= 0.60.
    """
    if predicted_direction != "NAIK":
        return "NO TRADE" if predicted_direction == "NO_TRADE" else "HOLD"
    if prob is not None:
        strong_at = buy_threshold * 1.10 if buy_threshold else STRONG_BUY_FALLBACK_PROB
        if float(prob) >= strong_at:
            return "STRONG BUY"
    return "BUY"
