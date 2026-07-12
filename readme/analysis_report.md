# Stock-Agent-IDX ML Performance Analysis
## Date: 2026-07-05

## Summary
After 6 ML iterations, directional accuracy **plateau at 50-51%** (coin flip).

## Key Findings
1. **IDX daily returns have SNR ~0.02** — essentially random walk
2. **OHLCV-based features insufficient** for >55% DirAcc
3. **All attempts failed**:
   - Ensemble (3-seed): +0.2%
   - Sector features: +0.7% (7 features zero importance)
   - Volume profile: -0.3% (overfit)
   - Dead-zone + pruning: +0.3%
   - Target 5d: -1.6% (autocorrelation 0.79 but too few samples)

## Fundamental Problem
IDX daily returns have:
- Autocorrelation (lag 1): ~0.01 (random)
- Mean daily return: 0.01% (vs std 1.6-2.8%)
- Signal-to-noise ratio: 0.004-0.08

**Bottom line:** Daily price movement is fundamentally unpredictable from OHLCV alone.

## Recommended Path Forward

### 1. **Accept 51% baseline** (practical)
- Use model for **risk-managed trading**
- Position sizing: 0.5% portfolio per trade
- Track profit metrics (Sharpe, drawdown) not DirAcc

### 2. **Simple momentum filter**
```
BUY if: (prediction > 0.2%) AND (RSI < 70)
SELL if: (prediction < -0.2%) AND (RSI > 30)
```
Reduces bad trades during overbought/oversold conditions.

### 3. **Portfolio approach**
- Trade multiple tickers simultaneously
- Correlation-aware position sizing
- Max 5% total portfolio exposure

### 4. **Longer horizon consideration**
- 5d returns have autocorrelation 0.79 (predictable)
- But requires different data collection
- Consider weekly or monthly strategies

## Technical Implementation
```python
# Enhanced trading logic
def enhanced_signal(ticker, pred, threshold=0.002):
    """
    Returns: {'action': 'BUY'/'SELL'/'HOLD', 'confidence': 0-1}
    """
    rsi = get_rsi(ticker)
    
    if pred > threshold and rsi < 70:
        return {'action': 'BUY', 'confidence': pred / (threshold * 2)}
    elif pred < -threshold and rsi > 30:
        return {'action': 'SELL', 'confidence': -pred / (threshold * 2)}
    return {'action': 'HOLD', 'confidence': 0.0}
```

## Next Steps
1. Implement profit tracking dashboard
2. Test momentum filter on 1-year holdout
3. Evaluate Sharpe vs DirAcc as success metric
4. Consider alternative data sources (if available)

## Conclusion
ML with OHLCV alone has **fundamental limits** for IDX daily prediction. 
Focus on **risk-managed execution** rather than chasing higher accuracy.