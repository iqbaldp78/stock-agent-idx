"""
Agents module — Multi-agent analysis system
"""
from agents.bandarmologi import analyze as analyze_bandarmologi
from agents.fundamental import analyze as analyze_fundamental
from agents.technical import analyze as analyze_technical
from agents.macro import analyze as analyze_macro
from agents.news import analyze as analyze_news
from agents.investment_manager import synthesize

__all__ = [
    "analyze_bandarmologi",
    "analyze_fundamental",
    "analyze_technical",
    "analyze_macro",
    "analyze_news",
    "synthesize",
]