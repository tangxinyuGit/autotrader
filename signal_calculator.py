import pandas as pd
import sqlite3
import numpy as np

DB_PATH = "stock_data.db"

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM stock_daily ORDER BY date ASC", conn)
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

def calculate_signals(df):
    """
    Calculates technical and fundamental signals.
    """
    df = df.copy()

    # 1. PE Percentiles (Rolling)
    # 5 Years approx 1250 trading days
    # 10 Years approx 2500 trading days
    # We use min_periods to allow calculation even if we don't have full history at the start
    df['pe_rank_5y'] = df['pe_ttm'].rolling(window=1250, min_periods=250).rank(pct=True)
    df['pe_rank_10y'] = df['pe_ttm'].rolling(window=2500, min_periods=250).rank(pct=True)

    # 2. Sentiment: Bias 20
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['bias_20'] = (df['close'] - df['ma20']) / df['ma20']

    # 3. Sentiment: Volume Ratio (MA5 / MA60)
    df['vol_ma5'] = df['volume'].rolling(window=5).mean()
    df['vol_ma60'] = df['volume'].rolling(window=60).mean()
    df['vol_ratio'] = df['vol_ma5'] / df['vol_ma60']

    # 4. Macro: Northbound Net Inflow (20 days sum)
    df['north_inflow_20'] = df['north_net_inflow'].rolling(window=20).sum()

    # 5. Macro: Bond Yield Trend (Current < MA60)
    df['bond_ma60'] = df['cn10y'].rolling(window=60).mean()
    df['bond_trend_down'] = df['cn10y'] < df['bond_ma60']

    return df

def get_latest_signal():
    df = load_data()
    df = calculate_signals(df)
    return df.iloc[-1]

if __name__ == "__main__":
    df = load_data()
    df_signals = calculate_signals(df)
    print("Signals Calculated. Latest Data:")
    print(df_signals[['close', 'pe_ttm', 'pe_rank_5y', 'bias_20', 'vol_ratio', 'north_inflow_20', 'bond_trend_down']].tail())
