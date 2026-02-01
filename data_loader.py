import akshare as ak
import pandas as pd
import sqlite3
from datetime import datetime
import time

DB_PATH = "stock_data.db"

def fetch_price_data(symbol="sz399006"):
    print(f"Fetching Price Data for {symbol}...")
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df[['open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        print(f"Error fetching price data: {e}")
        return pd.DataFrame()

def fetch_valuation_data():
    # Using "创业板50" as a proxy for "创业板指" valuation as AkShare Legu interface supports it.
    symbol = "创业板50"
    print(f"Fetching Valuation Data for {symbol} (Proxy for 399006)...")
    try:
        # PE
        df_pe = ak.stock_index_pe_lg(symbol=symbol)
        df_pe['date'] = pd.to_datetime(df_pe['日期'])
        df_pe.set_index('date', inplace=True)
        df_pe = df_pe[['滚动市盈率']]
        df_pe.columns = ['pe_ttm']

        # PB
        df_pb = ak.stock_index_pb_lg(symbol=symbol)
        df_pb['date'] = pd.to_datetime(df_pb['日期'])
        df_pb.set_index('date', inplace=True)
        # Check available columns
        col_name = '市净率' if '市净率' in df_pb.columns else df_pb.columns[2]
        df_pb = df_pb[[col_name]]
        df_pb.columns = ['pb']

        # Merge
        df_val = pd.concat([df_pe, df_pb], axis=1)
        return df_val
    except Exception as e:
        print(f"Error fetching valuation data: {e}")
        return pd.DataFrame()

def fetch_macro_data():
    print("Fetching 10Y Bond Yield...")
    try:
        df = ak.bond_zh_us_rate(start_date="20150101")
        df['date'] = pd.to_datetime(df['日期'])
        df.set_index('date', inplace=True)
        df = df[['中国国债收益率10年']]
        df.columns = ['cn10y']
        return df
    except Exception as e:
        print(f"Error fetching bond data: {e}")
        return pd.DataFrame()

def fetch_northbound_data():
    print("Fetching Northbound Fund Flow...")
    try:
        df = ak.stock_hsgt_hist_em(symbol="北向资金")
        df['date'] = pd.to_datetime(df['日期'])
        df.set_index('date', inplace=True)
        df = df[['当日成交净买额']]
        df.columns = ['north_net_inflow']
        # Convert to float (it might be in 100 millions or something, usually 100M RMB unit in this API?
        # Check sample: -7.7299. Usually Unit is 100 Million RMB (Yi).
        # We will keep it as is.
        return df
    except Exception as e:
        print(f"Error fetching northbound data: {e}")
        return pd.DataFrame()

def update_database():
    print("Starting Data Update...")

    df_price = fetch_price_data()
    df_val = fetch_valuation_data()
    df_macro = fetch_macro_data()
    df_north = fetch_northbound_data()

    if df_price.empty:
        print("Critical: No price data. Aborting.")
        return

    # Merge
    print("Merging data...")
    # Left join on price dates
    df_merged = df_price.join(df_val, how='left')
    df_merged = df_merged.join(df_macro, how='left')
    df_merged = df_merged.join(df_north, how='left')

    # Fill NaN
    # Valuation and Macro data might have gaps (holidays different from stock market?).
    # Forward fill is appropriate for PE and Bond yields.
    df_merged['pe_ttm'] = df_merged['pe_ttm'].ffill()
    df_merged['pb'] = df_merged['pb'].ffill()
    df_merged['cn10y'] = df_merged['cn10y'].ffill()

    # Northbound flow is daily flow. If NaN, it means no trading or missing.
    # Fill with 0 for "No Inflow/Outflow".
    if 'north_net_inflow' in df_merged.columns:
        df_merged['north_net_inflow'] = df_merged['north_net_inflow'].fillna(0)
    else:
        df_merged['north_net_inflow'] = 0.0

    # Save to SQLite
    print(f"Saving {len(df_merged)} rows to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    df_merged.to_sql('stock_daily', conn, if_exists='replace', index=True)
    conn.close()
    print("Database updated successfully.")

if __name__ == "__main__":
    update_database()
