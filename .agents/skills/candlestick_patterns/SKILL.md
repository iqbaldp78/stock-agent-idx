---
name: candlestick_patterns
description: Deteksi dan evaluasi pola candlestick saham BEI berdasarkan bentuk candle dan win-rate historis.
---

# Candlestick Patterns & Win-Rate BEI

Gunakan aturan berikut saat menganalisis pola candlestick saham IHSG/BEI:

### 1. Reversal Bullish
- **Hammer**: `lower_wick > 2 * body_size` AND `upper_wick < 0.3 * body_size` AND `volume > ma_volume_20`. (Win rate BEI: 64%, Konteks: setelah downtrend 3+ hari, target: 3 hari).
- **Morning Star**: Day 1 Bearish besar (body > 1%), Day 2 Doji/Small body, Day 3 Bullish > 50% menutup Day 1. (Win rate BEI: 71%, Konteks: di Support kuat + volume spike Day 3).
- **Bullish Engulfing**: Day 1 Bearish, Day 2 Bullish menelan Day 1 sepenuhnya, `volume_day2 > volume_day1 * 1.5`. (Win rate BEI: 68%).
- **Piercing Line**: Day 1 Bearish besar, Day 2 Open di bawah Low Day 1 & Close > 50% Body Day 1. (Win rate BEI: 61%).

### 2. Reversal Bearish
- **Shooting Star**: `upper_wick > 2 * body_size` AND `lower_wick < 0.3 * body_size` setelah Uptrend. (Win rate BEI: 63%, Signal: BEARISH).
- **Evening Star**: Day 1 Bullish besar, Day 2 Gap Up + small body, Day 3 Bearish besar (tutup < 50% Day 1). (Win rate BEI: 70%, Signal: BEARISH).
- **Bearish Engulfing**: Day 1 Bullish, Day 2 Bearish menelan Day 1. (Win rate BEI: 66%, Signal: BEARISH).

### 3. Continuation
- **Three White Soldiers**: 3 candle bullish berturut-turut, Open di dalam body candle sebelumnya, Close lebih tinggi, volume meningkat tiap hari. (Win rate BEI: 73%, Signal: STRONG BULLISH).
- **Rising Three**: Bullish besar, diikuti 3 candle kecil dalam range, diakhiri bullish besar lagi. (Win rate BEI: 69%).
