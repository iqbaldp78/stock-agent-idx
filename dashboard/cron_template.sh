#!/bin/bash
# Daily profit dashboard update
cd /home/hamboo/my-product/stock-agent-idx
python3 dashboard/profit_dashboard.py --threshold 0.003 --commission 0.001
