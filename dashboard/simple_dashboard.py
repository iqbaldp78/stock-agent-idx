#!/usr/bin/env python3
"""
Simple Profit Dashboard - No external dependencies
"""
import json
import os
from datetime import date
from pathlib import Path

def create_dashboard():
    """Create static dashboard based on our analysis."""
    
    # Data from our ML experiments (6 iterations)
    analysis_data = {
        "title": "Stock-Agent-IDX Profit Dashboard",
        "date": date.today().isoformat(),
        "summary": {
            "iterations": 6,
            "best_dir_acc": 51.1,
            "avg_dir_acc": 50.8,
            "target_dir_acc": 58,
            "status": "plateau",
            "conclusion": "OHLCV features alone insufficient for >55% DirAcc"
        },
        "profit_metrics": {
            "sharpe_target": 0.3,
            "profit_factor_target": 1.1,
            "max_drawdown_target": 6,
            "win_rate_target": 51,
            "current_estimate": {
                "sharpe": 0.18,
                "profit_factor": 1.08,
                "max_drawdown": 7.2,
                "win_rate": 51.1
            }
        },
        "key_insights": [
            "IDX daily returns have SNR ≈ 0.02 (near random walk)",
            "Autocorrelation AC1 ≈ 0.01 for 1d horizon, 0.79 for 5d",
            "All OHLCV-derived features show zero importance beyond basics",
            "Foreign flow data limited to 40 days (insufficient for 5y training)",
            "51% DirAcc = break-even after 0.1% commission"
        ],
        "recommendations": [
            "Accept 51% DirAcc as maximum with OHLCV-only data",
            "Focus on Sharpe ratio & profit factor instead of DirAcc",
            "Increase trade threshold to 0.3% (from 0.2%)",
            "Implement 1.5% stop-loss and take-profit",
            "Position sizing: 0.5% per trade, max 2% daily exposure",
            "Track monthly: Sharpe, drawdown, profit factor consistency"
        ],
        "experiment_history": [
            {"v": "v1", "dir_acc": 50.8, "change": "Baseline"},
            {"v": "v2", "dir_acc": 51.0, "change": "+ 3-seed ensemble"},
            {"v": "v3", "dir_acc": 51.7, "change": "+ Sector features"},
            {"v": "v4", "dir_acc": 50.5, "change": "+ Volume profile"},
            {"v": "v5", "dir_acc": 51.1, "change": "+ Prune 20 dead features + Dead-zone"},
            {"v": "v6", "dir_acc": 51.1, "change": "+ Consolidated features"}
        ]
    }
    
    # HTML dashboard
    html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{analysis_data["title"]}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .header h1 {{ margin: 0; color: #2563eb; }}
        .header .subtitle {{ color: #6b7280; margin-top: 5px; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .card.highlight {{ border-left: 4px solid #2563eb; }}
        .card.warning {{ border-left: 4px solid #f59e0b; }}
        .card.critical {{ border-left: 4px solid #ef4444; }}
        .metric-value {{ font-size: 2rem; font-weight: bold; margin: 10px 0; }}
        .metric-label {{ color: #6b7280; font-size: 0.9rem; }}
        .progress-bar {{ height: 8px; background: #e5e7eb; border-radius: 4px; margin: 10px 0; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: #10b981; }}
        .insights, .recommendations {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h2 {{ margin-top: 0; color: #374151; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; line-height: 1.5; }}
        .experiment-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .experiment-table th, .experiment-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        .experiment-table th {{ background: #f9fafb; font-weight: 600; color: #374151; }}
        .experiment-table tr:hover {{ background: #f9fafb; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }}
        .badge-good {{ background: #dcfce7; color: #166534; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-critical {{ background: #fee2e2; color: #991b1b; }}
        footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {analysis_data["title"]}</h1>
            <div class="subtitle">Analysis Date: {analysis_data["date"]} | 6 ML Iterations | Focus: Profit Metrics over Directional Accuracy</div>
        </div>

        <div class="cards">
            <div class="card highlight">
                <div class="metric-label">Best DirAcc Achieved</div>
                <div class="metric-value">{analysis_data["summary"]["best_dir_acc"]}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {analysis_data["summary"]["best_dir_acc"] / analysis_data["summary"]["target_dir_acc"] * 100}%"></div>
                </div>
                <div>Target: {analysis_data["summary"]["target_dir_acc"]}% <span class="badge badge-warning">Plateau</span></div>
            </div>
            
            <div class="card { 'warning' if analysis_data['profit_metrics']['current_estimate']['sharpe'] < analysis_data['profit_metrics']['sharpe_target'] else 'highlight' }">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">{analysis_data["profit_metrics"]["current_estimate"]["sharpe"]:.2f}</div>
                <div>Target: {analysis_data["profit_metrics"]["sharpe_target"]} <span class="badge {'badge-critical' if analysis_data['profit_metrics']['current_estimate']['sharpe'] < analysis_data['profit_metrics']['sharpe_target'] else 'badge-good'}">
                    { 'Below target' if analysis_data['profit_metrics']['current_estimate']['sharpe'] < analysis_data['profit_metrics']['sharpe_target'] else 'Above target' }
                </span></div>
            </div>
            
            <div class="card { 'warning' if analysis_data['profit_metrics']['current_estimate']['profit_factor'] < analysis_data['profit_metrics']['profit_factor_target'] else 'highlight' }">
                <div class="metric-label">Profit Factor</div>
                <div class="metric-value">{analysis_data["profit_metrics"]["current_estimate"]["profit_factor"]:.2f}</div>
                <div>Target: {analysis_data["profit_metrics"]["profit_factor_target"]} <span class="badge {'badge-warning' if analysis_data['profit_metrics']['current_estimate']['profit_factor'] < analysis_data['profit_metrics']['profit_factor_target'] else 'badge-good'}">
                    { 'Thin margin' if analysis_data['profit_metrics']['current_estimate']['profit_factor'] < analysis_data['profit_metrics']['profit_factor_target'] else 'Profitable' }
                </span></div>
            </div>
            
            <div class="card { 'critical' if analysis_data['profit_metrics']['current_estimate']['max_drawdown'] > analysis_data['profit_metrics']['max_drawdown_target'] else 'highlight' }">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value">{analysis_data["profit_metrics"]["current_estimate"]["max_drawdown"]}%</div>
                <div>Target: <{analysis_data["profit_metrics"]["max_drawdown_target"]}% <span class="badge {'badge-critical' if analysis_data['profit_metrics']['current_estimate']['max_drawdown'] > analysis_data['profit_metrics']['max_drawdown_target'] else 'badge-good'}">
                    { 'High risk' if analysis_data['profit_metrics']['current_estimate']['max_drawdown'] > analysis_data['profit_metrics']['max_drawdown_target'] else 'Acceptable' }
                </span></div>
            </div>
        </div>

        <div class="insights">
            <h2>🔍 Key Insights from 6 ML Iterations</h2>
            <ul>
                {''.join(f'<li>{insight}</li>' for insight in analysis_data['key_insights'])}
            </ul>
        </div>

        <div class="recommendations">
            <h2>🎯 Profit-Based Recommendations</h2>
            <ul>
                {''.join(f'<li>{rec}</li>' for rec in analysis_data['recommendations'])}
            </ul>
        </div>

        <div class="card">
            <h2>📈 Experiment History</h2>
            <table class="experiment-table">
                <thead>
                    <tr>
                        <th>Version</th>
                        <th>DirAcc</th>
                        <th>Change</th>
                        <th>Result</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(
                        f'<tr>'
                        f'<td>{exp["v"]}</td>'
                        f'<td>{exp["dir_acc"]}%</td>'
                        f'<td>{exp["change"]}</td>'
                        f'<td><span class="badge { "badge-good" if exp["dir_acc"] > 51 else "badge-warning" }">'
                        f'{ "✓ Improvement" if exp["dir_acc"] > 51 else "→ No gain" }</span></td>'
                        f'</tr>'
                        for exp in analysis_data['experiment_history']
                    )}
                </tbody>
            </table>
        </div>

        <footer>
            <p>Dashboard generated from comprehensive ML analysis (2026-07-05)</p>
            <p>Conclusion: {analysis_data["summary"]["conclusion"]} | Focus shift: Directional Accuracy → Profit Metrics</p>
            <p>Files: <code>dashboard/simple_dashboard.py</code> | <code>analysis_report.md</code> | <code>scripts/profit_tracker.py</code></p>
        </footer>
    </div>
</body>
</html>
'''
    
    # Save files
    output_dir = Path("dashboard/output")
    output_dir.mkdir(exist_ok=True)
    
    # Save JSON data
    with open(output_dir / "dashboard_data.json", "w") as f:
        json.dump(analysis_data, f, indent=2)
    
    # Save HTML dashboard
    with open(output_dir / "index.html", "w") as f:
        f.write(html_template)
    
    print(f"✅ Dashboard deployed to {output_dir}/")
    print(f"   - index.html (main dashboard)")
    print(f"   - dashboard_data.json (data)")
    print()
    print("📊 Key Metrics:")
    print(f"   DirAcc: {analysis_data['summary']['best_dir_acc']}% (target: {analysis_data['summary']['target_dir_acc']}%)")
    print(f"   Sharpe: {analysis_data['profit_metrics']['current_estimate']['sharpe']:.2f} (target: {analysis_data['profit_metrics']['sharpe_target']})")
    print(f"   Profit factor: {analysis_data['profit_metrics']['current_estimate']['profit_factor']:.2f} (target: {analysis_data['profit_metrics']['profit_factor_target']})")
    print()
    print("💡 Recommendation: Focus on profit metrics (Sharpe, profit factor) instead of chasing >55% DirAcc")
    print("   With 51% DirAcc + proper risk management = possible profitability")


if __name__ == "__main__":
    create_dashboard()