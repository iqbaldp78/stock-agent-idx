# Deployment Guide - Realtime Stockbit Integration

## Overview
Deployment dari fitur realtime Stockbit integration untuk IHSG dan Portfolio Analyzer.

## Files Modified
1. `data/fetcher_stockbit.py` - IHSG realtime price function
2. `web-backend/main.py` - Updated `/api/ihsg` endpoint
3. `agents/portfolio_advisor.py` - Realtime prices dalam portfolio analysis
4. `web-frontend/src/app/(app)/ihsg/page.tsx` - Display realtime IHSG
5. `web-frontend/src/app/(app)/portfolio/page.tsx` - Display realtime indicators

## Deployment Steps

### 1. Pre-Deployment Checks
```bash
# Verify syntax of modified Python files
python3 -c "
import ast
import sys
files = [
    'web-backend/main.py',
    'data/fetcher_stockbit.py',
    'agents/portfolio_advisor.py'
]
for f in files:
    try:
        with open(f) as file:
            ast.parse(file.read())
        print(f'✅ {f}')
    except SyntaxError as e:
        print(f'❌ {f}: {e}')
        sys.exit(1)
"

# Run tests
python3 test_realtime_integration.py
```

### 2. Git Commit & Push
```bash
# Create feature branch
git checkout -b feat/realtime-stockbit-integration

# Stage changes
git add data/fetcher_stockbit.py
git add web-backend/main.py
git add agents/portfolio_advisor.py
git add web-frontend/src/app/\(app\)/ihsg/page.tsx
git add web-frontend/src/app/\(app\)/portfolio/page.tsx
git add REALTIME_STOCKBIT_INTEGRATION.md
git add test_realtime_integration.py

# Commit
git commit -m "feat: integrate realtime Stockbit prices for IHSG and portfolio analysis

- Add get_ihsg_realtime_price_stockbit() to fetch IHSG realtime from Stockbit API
- Update /api/ihsg endpoint to include realtime price data alongside predictions
- Integrate realtime ticker prices in portfolio_advisor.py via parallel fetch
- Update frontend IHSG page to display realtime price indicator with live ticker
- Update frontend portfolio page to show realtime price badge and info
- Add fallback mechanism for Stockbit API unavailability
- All DCA recommendations now based on current market prices

Benefits:
- Portfolio analysis uses latest market data
- Better rebalancing recommendations
- Target prices and lots calculated accurately
- Frontend shows live price updates with timestamp

Testing:
- Run: python3 test_realtime_integration.py
- Test /api/ihsg endpoint for realtime field
- Verify portfolio AI analysis uses realtime prices"

# Push to production
git push -u origin feat/realtime-stockbit-integration
```

### 3. Create Pull Request
```bash
# Using GitHub CLI (if available)
gh pr create \
  --title "feat: realtime Stockbit integration" \
  --body "Integrate realtime prices from Stockbit API for IHSG and portfolio analysis" \
  --base main \
  --head feat/realtime-stockbit-integration
```

### 4. Post-Deployment Verification

#### Backend API Tests
```bash
# Test IHSG endpoint
curl -X GET http://localhost:8000/api/ihsg \
  -H "Authorization: Bearer <token>" \
  | jq '.realtime'

# Should see:
# {
#   "price": 7250.45,
#   "prev_close": 7200.00,
#   "change": 50.45,
#   "change_pct": 0.70,
#   "timestamp": "2026-07-18T08:45:00",
#   "source": "stockbit"
# }
```

#### Frontend Verification
- Visit `/ihsg` page → should see "📡 IHSG Realtime (Stockbit)" card
- Visit `/portfolio` → should see "📡 Realtime Prices" badge
- Check browser console for errors

#### Performance Check
```bash
# Monitor API response times
time curl -X GET http://localhost:8000/api/ihsg \
  -H "Authorization: Bearer <token>" > /dev/null

# Should complete in < 2 seconds
```

### 5. Rollback (if needed)
```bash
# Revert to previous stable commit
git revert <commit-hash>
git push origin main

# OR reset branch
git reset --hard <previous-commit>
git push -f origin main
```

## Configuration

### Required Environment Variables
Ensure these are set in `.env`:
```
STOCKBIT_API_KEY=<your-api-key>
STOCKBIT_REFRESH_TOKEN=<your-refresh-token>
```

If tokens expire:
```bash
python3 -c "
from data.fetcher_stockbit import refresh_stockbit_token
token = refresh_stockbit_token()
print(f'New token: {token}')
"
```

## Monitoring

### Log Files
```bash
# Check backend logs
tail -f app.log | grep "IHSG\|Realtime\|Portfolio"

# Check specific errors
grep -i "error" app.log | grep -E "ihsg|stockbit"
```

### Metrics
- Response time for `/api/ihsg` (target: < 1.5s)
- Response time for `/api/portfolio/ai-analysis` (target: < 3s)
- Stockbit API availability (monitor 401/403 errors)

## Troubleshooting

### Issue: Stockbit API 401/403
**Solution:** Token expired
```bash
python3 -c "from data.fetcher_stockbit import refresh_stockbit_token; refresh_stockbit_token()"
```

### Issue: Portfolio analysis slower than before
**Solution:** Parallel fetch of prices might be hitting rate limits
- Check Stockbit API logs
- Reduce max_workers from 5 to 3 in `_get_realtime_prices()`

### Issue: Realtime prices not displaying in UI
**Solution:** Check browser console for API errors
- Verify token is valid
- Check if Stockbit API is down
- Fallback should show error message

## Rollout Schedule (Recommended)
1. **Stage 1 (Hour 0-1):** Deploy to staging environment
2. **Stage 2 (Hour 1-2):** Run smoke tests and manual verification
3. **Stage 3 (Hour 2+):** Deploy to production during low-traffic hours
4. **Stage 4 (Ongoing):** Monitor logs and metrics for 24 hours

## Success Criteria
✅ All files syntactically correct
✅ Tests pass: `python3 test_realtime_integration.py`
✅ `/api/ihsg` includes `realtime` field
✅ Portfolio page shows realtime price indicators
✅ No 5xx errors in logs
✅ API response times acceptable (< 3s)
✅ Stockbit token auto-refresh working
