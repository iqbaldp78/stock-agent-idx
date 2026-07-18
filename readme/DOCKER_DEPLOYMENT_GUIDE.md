📋 REALTIME STOCKBIT + WIB TIMEZONE - DOCKER COMPOSE DEPLOYMENT
═══════════════════════════════════════════════════════════════

STATUS: ✅ READY FOR PRODUCTION DEPLOYMENT
Updated: 18/7/2026, 11:23 WIB

═══════════════════════════════════════════════════════════════
CHANGES SUMMARY
═══════════════════════════════════════════════════════════════

✅ CODE CHANGES (5 files modified):
   1. agents/portfolio_advisor.py
      - Import: timezone, timedelta
      - Format generated_at as WIB
      - Update _error_response() to use WIB timestamp

   2. data/fetcher_stockbit.py
      - NEW: get_ihsg_realtime_price_stockbit()
      - NEW: _ihsg_realtime_fallback()
      - Format all timestamps as 'YYYY-MM-DD HH:MM:SS WIB'

   3. web-backend/main.py
      - UPDATED: /api/ihsg endpoint
      - Now includes realtime field with live Stockbit data
      - No breaking changes to existing fields

   4. web-frontend/src/app/(app)/ihsg/page.tsx
      - NEW: Realtime price card display
      - Shows: price, prev_close, change, change_pct, timestamp
      - Animated gradient with pulse indicator

   5. web-frontend/src/app/(app)/portfolio/page.tsx
      - NEW: Realtime price badges on Holdings & DCA sections
      - Live price update indicators

✅ DOCKER COMPOSE CHANGES (1 file modified):
   docker-compose.yml
   - postgres: added TZ=Asia/Jakarta
   - app: added TZ=Asia/Jakarta
   - web_api: added TZ=Asia/Jakarta
   - web_frontend: added TZ=Asia/Jakarta

✅ DOCUMENTATION & SCRIPTS:
   - REALTIME_STOCKBIT_INTEGRATION.md
   - DEPLOYMENT.md
   - test_realtime_integration.py
   - deploy-to-docker.sh

═══════════════════════════════════════════════════════════════
DEPLOYMENT STEPS (COPY & PASTE)
═══════════════════════════════════════════════════════════════

STEP 1: Stage all changes
────────────────────────
git add .

STEP 2: Commit
────────────────────────
git commit -m "feat: integrate realtime Stockbit prices with WIB timezone

FEATURES:
- Realtime IHSG price from Stockbit API
- Realtime ticker prices for portfolio analysis
- Frontend live price indicators

TIMEZONE:
- All services: TZ=Asia/Jakarta
- Timestamps: YYYY-MM-DD HH:MM:SS WIB format

DEPLOYMENT:
- docker-compose pull
- docker-compose up -d --build"

STEP 3: Push to remote
────────────────────────
git push -u origin feat/realtime-stockbit-wib-timezone

Or merge directly to main:
git checkout main
git pull origin main
git merge feat/realtime-stockbit-wib-timezone
git push origin main

STEP 4: Deploy to Docker Compose
────────────────────────
docker-compose pull
docker-compose up -d --build

Wait for all services to start (≈30-60 seconds)

STEP 5: Verify Deployment
────────────────────────
# Test IHSG endpoint
curl -X GET http://localhost:8000/api/ihsg \
  -H "Authorization: Bearer <your-token>" | jq '.realtime'

Expected response:
{
  "price": 7250.45,
  "prev_close": 7200.00,
  "change": 50.45,
  "change_pct": 0.70,
  "timestamp": "18/7/2026 11:24:33 WIB",
  "currency": "IDR",
  "source": "stockbit"
}

STEP 6: Check Frontend
────────────────────────
Visit: http://localhost:3000/ihsg
Should see: "📡 IHSG Realtime (Stockbit)" card with live data

Visit: http://localhost:3000/portfolio
Should see: "📡 Realtime Prices" badges

═══════════════════════════════════════════════════════════════
DOCKER COMPOSE CHANGES DETAIL
═══════════════════════════════════════════════════════════════

postgres service:
  environment:
    TZ: Asia/Jakarta  # ← NEW

app service:
  environment:
    TZ: Asia/Jakarta  # ← NEW

web_api service:
  environment:
    - TZ=Asia/Jakarta  # ← NEW

web_frontend service:
  environment:
    - TZ=Asia/Jakarta  # ← NEW

═══════════════════════════════════════════════════════════════
VERIFICATION CHECKLIST
═══════════════════════════════════════════════════════════════

After docker-compose up -d --build:

Backend:
☐ Container web_user_api is running
  docker ps | grep web_user_api
  
☐ API responds with realtime field
  curl http://localhost:8000/api/ihsg | jq '.realtime'
  
☐ Timestamps show WIB format (not ISO)
  Check: "2026-07-18 11:24:33 WIB"

☐ No errors in logs
  docker logs web_user_api | grep -i error

Frontend:
☐ Container web_user_frontend is running
  docker ps | grep web_user_frontend
  
☐ IHSG page loads at http://localhost:3000/ihsg
☐ Realtime card visible with live data
☐ Portfolio page shows realtime badges
☐ No console errors (F12 → Console)

Database:
☐ PostgreSQL running with TZ=Asia/Jakarta
  docker exec stock_postgres date
  Should show: +07:00 offset

═══════════════════════════════════════════════════════════════
TROUBLESHOOTING
═══════════════════════════════════════════════════════════════

Issue: Realtime prices not showing (404 or null)
─────────────────────────────────────────────────
Solution:
1. Check STOCKBIT_API_KEY in .env
2. Check container logs: docker logs web_user_api
3. Verify Stockbit API is accessible

Issue: Timestamps still in ISO format (not WIB)
─────────────────────────────────────────────────
Solution:
1. Verify TZ=Asia/Jakarta in docker-compose.yml
2. Rebuild containers: docker-compose up -d --build
3. Check container timezone: docker exec web_user_api date

Issue: API response time > 3 seconds
─────────────────────────────────────────────────
Solution:
1. Check network connectivity to Stockbit API
2. Reduce max_workers from 5 to 3 in portfolio_advisor.py
3. Check server resources (CPU, memory)

═══════════════════════════════════════════════════════════════
ROLLBACK (if needed)
═══════════════════════════════════════════════════════════════

Option 1: Quick rollback to previous version
─────────────────────────────────────────────
git revert <commit-hash>
git push origin main
docker-compose pull
docker-compose up -d --build

Option 2: Temporary disable realtime
─────────────────────────────────────────────
Edit web-backend/main.py line 514:
# realtime_data = get_ihsg_realtime_price_stockbit()
realtime_data = {}  # Disabled temporarily

Then rebuild:
docker-compose up -d --build

═══════════════════════════════════════════════════════════════
MONITORING
═══════════════════════════════════════════════════════════════

Check API performance:
─────────────────────
docker logs web_user_api | grep "IHSG Realtime\|Portfolio"

Monitor timestamps:
─────────────────────
curl http://localhost:8000/api/ihsg | jq '.realtime.timestamp'
Should show: "2026-07-18 11:24:33 WIB"

Check database timezone:
─────────────────────
docker exec stock_postgres psql -U vectoruser -d vectoragent -c "SELECT NOW();"
Should show: timestamp with +07:00

═══════════════════════════════════════════════════════════════
NEXT STEPS
═══════════════════════════════════════════════════════════════

1. ✅ Execute git commands above (Steps 1-3)
2. ✅ Deploy to docker: docker-compose pull && docker-compose up -d --build
3. ✅ Run verification checklist
4. ✅ Monitor logs for 24 hours
5. ✅ Collect user feedback

═══════════════════════════════════════════════════════════════
