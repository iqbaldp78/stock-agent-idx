import re

with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'r') as f:
    content = f.read()

# Replace weight logic
old_weight_block = """        # Weighted combination
        # Incorporating News Sentiment Score (15% weight), reducing others slightly
        combined_score = (
            momentum_score * 0.30 +
            breadth_score * 0.25 +
            macro_score * 0.15 +
            sector_score * 0.15 +
            news_sentiment_score * 0.15
        )"""

new_weight_block = """        # Weighted combination
        # Tuned to rely heavily on Breadth and Momentum to reduce noise and regression to mean
        combined_score = (
            breadth_score * 0.60 +
            momentum_score * 0.25 +
            news_sentiment_score * 0.15
        )"""

# Replace direction logic
old_dir_block = """        # Direction determination
        if combined_score > 0.6:
            direction = "BULLISH"
        elif combined_score < 0.4:
            direction = "BEARISH"
        else:
            direction = "SIDEWAYS"

        # Confidence (based on score agreement)"""

new_dir_block = """        # Direction determination (Tightened threshold from 0.4-0.6 to 0.48-0.52)
        if combined_score > 0.52:
            direction = "BULLISH"
        elif combined_score < 0.48:
            direction = "BEARISH"
        else:
            direction = "SIDEWAYS"

        # Confidence (based on score agreement)"""

content = content.replace(old_weight_block, new_weight_block)
content = content.replace(old_dir_block, new_dir_block)

with open('/home/hamboo/my-product/stock-agent-idx/agents/ihsg_predictor.py', 'w') as f:
    f.write(content)
