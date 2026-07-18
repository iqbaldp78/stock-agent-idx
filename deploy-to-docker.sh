#!/bin/bash
# ============================================================
# REALTIME STOCKBIT INTEGRATION + WIB TIMEZONE
# PRODUCTION DEPLOYMENT TO DOCKER COMPOSE
# ============================================================
# Updated: 18/7/2026, 11:23 WIB
# ============================================================

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  🚀 DEPLOYING REALTIME STOCKBIT + WIB TIMEZONE            ║"
echo "║  Status: Ready for Production Docker Compose             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Verify git status
echo "📋 Step 1: Checking git status..."
echo ""
git status --short
echo ""

# Step 2: Show what will be committed
echo "📦 Step 2: Files to be committed:"
echo ""
echo "Modified (5 files):"
echo "  • agents/portfolio_advisor.py"
echo "  • data/fetcher_stockbit.py"
echo "  • web-backend/main.py"
echo "  • web-frontend/src/app/(app)/ihsg/page.tsx"
echo "  • web-frontend/src/app/(app)/portfolio/page.tsx"
echo "  • docker-compose.yml (NEW - TZ=Asia/Jakarta added)"
echo ""
echo "Documentation & Tests (10+ files):"
echo "  • REALTIME_STOCKBIT_INTEGRATION.md"
echo "  • DEPLOYMENT.md"
echo "  • test_realtime_integration.py"
echo "  • And more..."
echo ""

# Step 3: Create feature branch
echo "🌿 Step 3: Creating feature branch..."
git checkout -b feat/realtime-stockbit-wib-timezone 2>/dev/null || git checkout feat/realtime-stockbit-wib-timezone
echo "✅ Branch: $(git rev-parse --abbrev-ref HEAD)"
echo ""

# Step 4: Stage all changes
echo "📦 Step 4: Staging all changes..."
git add .
echo "✅ All files staged"
echo ""

# Step 5: Show summary
echo "✅ Step 5: Changes summary:"
echo ""
git status --short
echo ""

# Step 6: Commit
echo "💾 Step 6: Committing changes..."
git commit -m "feat: integrate realtime Stockbit prices with WIB timezone

FEATURES:
- Add get_ihsg_realtime_price_stockbit() for live IHSG price from Stockbit API
- Update /api/ihsg endpoint to include realtime field
- Integrate realtime ticker prices in portfolio AI analysis (parallel fetch, 5 workers)
- Update frontend IHSG page with realtime price indicator
- Update frontend portfolio page with realtime price badges

TIMEZONE:
- Add TZ=Asia/Jakarta to all docker-compose services
- Format all timestamps as 'YYYY-MM-DD HH:MM:SS WIB'
- Timestamps in portfolio advisor, IHSG fetcher, error responses
- Consistent timezone across all services

DOCKER-COMPOSE CHANGES:
- postgres: TZ=Asia/Jakarta
- app: TZ=Asia/Jakarta
- web_api: TZ=Asia/Jakarta
- web_frontend: TZ=Asia/Jakarta

BENEFITS:
✓ Real-time market data for better recommendations
✓ All timestamps in WIB (Indonesia timezone)
✓ Portfolio analysis uses current prices
✓ Accurate target prices and allocations
✓ Frontend shows live price updates

DEPLOYMENT:
1. docker-compose pull
2. docker-compose up -d --build
3. Verify endpoints: curl http://localhost:8000/api/ihsg

Testing:
- Run: python3 test_realtime_integration.py
- Check /api/ihsg for realtime field
- Verify frontend displays live indicators
- Confirm timestamps show WIB format"

echo "✅ Committed successfully"
echo ""
echo "Commit hash: $(git rev-parse --short HEAD)"
echo ""

# Step 7: Show push command
echo "🔼 Step 7: Ready to push!"
echo ""
echo "Run this to push to remote:"
echo ""
echo "  git push -u origin feat/realtime-stockbit-wib-timezone"
echo ""
echo "Or merge directly to main (if authorized):"
echo ""
echo "  git checkout main"
echo "  git pull origin main"
echo "  git merge feat/realtime-stockbit-wib-timezone"
echo "  git push origin main"
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ✅ COMMIT READY FOR PRODUCTION                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Next: Push changes and deploy to docker-compose"
echo ""
