import pandas as pd
from datetime import date
df = pd.DataFrame({'Close': [100, 110]}, index=['2026-07-23', '2026-07-24'])
print("df:")
print(df)
trade_date = '2026-07-24'
future_data = df.loc[df.index > trade_date]
print("\nfuture_data (> trade_date):")
print(future_data)
