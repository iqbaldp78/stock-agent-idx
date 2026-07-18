#!/bin/bash
# ============================================================
# REALTIME STOCKBIT INTEGRATION - DEPLOYMENT SCRIPT
# ============================================================
# Run this script to deploy the realtime integration to production
# Usage: bash deploy.sh
# ============================================================

set -e

echo "🚀 Starting Realtime Stockbit Integration Deployment..."
echo ""

# Step 1: Check git status
echo "📋 Step 1: Checking git status..."
git status
echo ""

# Step 2: Create feature branch
echo "🌿 Step 2: Creating feature branch..."
git checkout -b feat/realtime-stockbit-integration
echo "✅ Feature branch created"
echo ""

# Step 3: Stage all changes
echo "📦 Step 3: Staging changes..."
git add data/fetcher_stockbit.py
git add web-backend/main.py
git add agents/portfolio_advisor.py
git add "web-frontend/src/app/(app)/ihsg/page.tsx"
git add "web-frontend/src/app/(app)/portfolio/page.tsx"
git add REALTIME_STOCKBIT_INTEGRATION.md
git add DEPLOYMENT.md
git add test_realtime_integration.py
git add DEPLOYMENT_CHECKLIST.md
git add .github/workflows/deploy-realtime.yml
echo "✅ All changes staged"
echo ""

# Step 4: Verify staged changes
echo "✅ Step 4: Verifying staged changes..."
git status
echo ""

# Step 5: Commit
echo "💾 Step 5: Committing changes..."
git commit -m "feat: integrate realtime Stockbit prices for IHSG and portfolio analysis

- Add get_ihsg_realtime_price_stockbit() to fetch IHSG realtime from Stockbit API
- Update /api/ihsg endpoint to include realtime price data (price, change, change_pct, timestamp)
- Integrate realtime ticker prices in portfolio_advisor.py via parallel fetch (5 workers)
- Update frontend IHSG page to display realtime price indicator with live ticker
- Update frontend portfolio page with realtime price badges on holdings and DCA sections
- Add fallback mechanism for Stockbit API unavailability
- All DCA recommendations now calculated with current market prices

Benefits:
✓ Portfolio analysis uses latest market data
✓ Better rebalancing recommendations based on current prices
✓ Target prices and lots calculated accurately
✓ Frontend shows live price updates with timestamp
✓ Graceful degradation if Stockbit API unavailable

Testing:
- Run: python3 test_realtime_integration.py
- Test /api/ihsg endpoint for realtime field
- Verify portfolio AI analysis uses realtime prices
- Check frontend displays realtime indicators"

echo "✅ Changes committed"
echo ""

# Step 6: Push to production
echo "🔼 Step 6: Pushing to production..."
git push -u origin feat/realtime-stockbit-integration
echo "✅ Pushed to origin"
echo ""

# Step 7: Show PR creation command
echo "🔗 Step 7: Creating Pull Request..."
echo ""
echo "Run this command to create PR:"
echo ""
echo "gh pr create \\"
echo "  --title 'feat: realtime Stockbit integration for IHSG and portfolio analysis' \\"
echo "  --body 'Integrate realtime prices from Stockbit API for IHSG and portfolio analyzer.' \\"
echo "  --base main \\"
echo "  --head feat/realtime-stockbit-integration"
echo ""

echo "✅ DEPLOYMENT SCRIPT COMPLETED!"
echo ""
echo "Next steps:"
echo "1. Run PR creation command above (if using GitHub CLI)"
echo "2. Review and merge PR on GitHub"
echo "3. Monitor deployment logs"
echo "4. Run post-deployment verification tests"
echo ""
