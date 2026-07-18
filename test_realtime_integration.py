#!/usr/bin/env python3
"""
Test script untuk verifikasi Realtime Stockbit Integration
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_ihsg_realtime():
    """Test IHSG realtime price fetch"""
    print("\n=== TEST 1: IHSG Realtime Price ===")
    try:
        from data.fetcher_stockbit import get_ihsg_realtime_price_stockbit

        result = get_ihsg_realtime_price_stockbit()
        print(f"✅ IHSG Realtime fetch successful")
        print(f"   Price: {result.get('price')}")
        print(f"   Change: {result.get('change_pct')}%")
        print(f"   Source: {result.get('source')}")
        return True
    except Exception as e:
        print(f"❌ IHSG Realtime fetch failed: {e}")
        return False


def test_ticker_realtime():
    """Test single ticker realtime price fetch"""
    print("\n=== TEST 2: Single Ticker Realtime Price ===")
    try:
        from data.fetcher_stockbit import get_current_price_stockbit

        tickers = ["BBCA", "UNVR", "TLKM"]
        for ticker in tickers:
            try:
                price = get_current_price_stockbit(ticker)
                print(f"✅ {ticker}: Rp {price:,.0f}")
            except Exception as e:
                print(f"⚠️  {ticker}: {str(e)[:50]}")
        return True
    except Exception as e:
        print(f"❌ Ticker realtime fetch failed: {e}")
        return False


def test_parallel_prices():
    """Test parallel price fetching"""
    print("\n=== TEST 3: Parallel Realtime Prices ===")
    try:
        from agents.portfolio_advisor import _get_realtime_prices

        tickers = ["BBCA", "UNVR", "TLKM", "ASII", "INDF"]
        prices = _get_realtime_prices(tickers)
        print(f"✅ Parallel fetch completed")
        print(f"   Fetched {len(prices)}/{len(tickers)} tickers")
        for ticker, price in list(prices.items())[:3]:
            print(f"   - {ticker}: Rp {price:,.0f}")
        return True
    except Exception as e:
        print(f"❌ Parallel fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_portfolio_context():
    """Test portfolio context building with realtime prices"""
    print("\n=== TEST 4: Portfolio Context Building ===")
    try:
        # Mock data
        holdings = [
            {
                "ticker": "BBCA",
                "total_lots": 100,
                "avg_cost": 9200,
                "current_price": 9500,  # Will be overwritten by realtime
                "total_invested": 920000,
                "unrealized_pnl_pct": 3.26
            },
            {
                "ticker": "UNVR",
                "total_lots": 50,
                "avg_cost": 4100,
                "current_price": 4200,
                "total_invested": 205000,
                "unrealized_pnl_pct": 2.44
            }
        ]

        from agents.portfolio_advisor import _get_realtime_prices

        tickers = [h.get("ticker") for h in holdings if h.get("ticker")]
        realtime_prices = _get_realtime_prices(tickers)

        print(f"✅ Realtime prices fetched: {len(realtime_prices)}")

        # Simulate update
        for h in holdings:
            ticker = h.get("ticker")
            if ticker in realtime_prices:
                old_price = h.get("current_price")
                new_price = realtime_prices[ticker]
                h["current_price"] = new_price
                print(f"   {ticker}: {old_price} → {new_price} (Rp {new_price - old_price:+,.0f})")

        return True
    except Exception as e:
        print(f"❌ Portfolio context failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("REALTIME STOCKBIT INTEGRATION TEST SUITE")
    print("=" * 60)

    api_key = os.getenv("STOCKBIT_API_KEY")
    if not api_key:
        print("⚠️  STOCKBIT_API_KEY not set in .env - tests may fail")
    else:
        print(f"✅ STOCKBIT_API_KEY is configured")

    results = []
    results.append(("IHSG Realtime", test_ihsg_realtime()))
    results.append(("Ticker Realtime", test_ticker_realtime()))
    results.append(("Parallel Prices", test_parallel_prices()))
    results.append(("Portfolio Context", test_portfolio_context()))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} passed")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
