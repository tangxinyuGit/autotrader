import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import data_loader
import signal_calculator
from main import load_state, run_backtest as run_daily_check # Reuse existing modules
import json
import os

# Set Page Config
st.set_page_config(page_title="ChiNext Quant Dashboard", layout="wide")

# --- Helper Functions ---
@st.cache_data
def load_market_data():
    """Load data efficiently"""
    df = signal_calculator.load_data()
    df = signal_calculator.calculate_signals(df)
    return df

def get_status_color(val, threshold, inverse=False):
    if inverse:
        return "green" if val > threshold else "red"
    return "green" if val < threshold else "red"

# --- Sidebar ---
st.sidebar.title("ChiNext Bot 🤖")

if st.sidebar.button("🔄 Update Data Now"):
    with st.spinner("Updating data from AkShare..."):
        try:
            data_loader.update_database()
            st.cache_data.clear() # Clear cache to reload new data
            st.success("Data Updated!")
        except Exception as e:
            st.error(f"Update Failed: {e}")

st.sidebar.markdown("---")
st.sidebar.header("Strategy Config")
buy_pe = st.sidebar.number_input("Buy PE Threshold", 0.0, 1.0, 0.30)
buy_vol = st.sidebar.number_input("Buy Vol Ratio", 0.0, 2.0, 0.60)
grid_drop = st.sidebar.number_input("Grid Drop", 0.0, 0.2, 0.05)

# --- Main Page ---
st.title("创业板指 (399006) Quant Dashboard")

# 1. Load Data
try:
    df = load_market_data()
    latest = df.iloc[-1]
except Exception as e:
    st.error("No data found. Please click 'Update Data Now'.")
    st.stop()

# 2. State & Positions
state = load_state()
positions = state.get("positions", [])
last_buy_price = state.get("last_buy_price")

# Calculate next grid level if holding
next_grid_price = None
if positions and last_buy_price:
    next_grid_price = last_buy_price * (1 - grid_drop)

# 3. Overview Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Price", f"{latest['close']:.2f}", f"{latest['close'] - df.iloc[-2]['close']:.2f}")
with col2:
    st.metric("PE-TTM", f"{latest['pe_ttm']:.2f}", f"Rank: {latest['pe_rank_5y']:.2%}")
with col3:
    st.metric("Vol Ratio", f"{latest['vol_ratio']:.2f}", delta_color="inverse")
with col4:
    pos_count = len(positions)
    st.metric("Positions", f"{pos_count} / 3", f"Last Buy: {last_buy_price if last_buy_price else '-'}")

# 4. Chart 1: Price & Grid
st.subheader("Market Trend & Grid Levels")

fig_price = make_subplots(rows=2, cols=1, shared_xaxes=True,
                          vertical_spacing=0.03, subplot_titles=('Price', 'Volume'),
                          row_heights=[0.7, 0.3])

# Candlestick
fig_price.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'],
                                   low=df['low'], close=df['close'], name='OHLC'), row=1, col=1)

# MA Lines
fig_price.add_trace(go.Scatter(x=df.index, y=df['ma20'], line=dict(color='orange', width=1), name='MA20'), row=1, col=1)

# Grid Levels (If Holding)
if next_grid_price and len(positions) < 3:
    # Add a horizontal line for next buy
    fig_price.add_hline(y=next_grid_price, line_dash="dash", line_color="green", annotation_text=f"Next Grid Buy: {next_grid_price:.2f}")

    # Add annotation directly
    fig_price.add_annotation(
        x=df.index[-1],
        y=next_grid_price,
        text=f"Next Buy: {next_grid_price:.2f}",
        showarrow=True,
        arrowhead=1
    )

# Volume
fig_price.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume'), row=2, col=1)

fig_price.update_layout(height=600, xaxis_rangeslider_visible=False)
st.plotly_chart(fig_price, use_container_width=True)

# 5. Chart 2: Valuation
st.subheader("Valuation History (PE-TTM)")
fig_pe = go.Figure()
fig_pe.add_trace(go.Scatter(x=df.index, y=df['pe_ttm'], name='PE-TTM'))

# Percentile Bands (We can calculate dynamic bands, but static approximation is easier for visualization or rolling)
# Let's plot rolling percentiles on a secondary axis or just the raw PE
# Better: Plot PE and add horizontal lines for "Current 30%" and "Current 70%" levels (approx)
# Or better: Plot the rank directly.
fig_pe_rank = go.Figure()
fig_pe_rank.add_trace(go.Scatter(x=df.index, y=df['pe_rank_5y'], name='PE Rank 5Y', fill='tozeroy'))
fig_pe_rank.add_hline(y=0.3, line_dash="dash", line_color="green", annotation_text="Buy Zone (<30%)")
fig_pe_rank.add_hline(y=0.7, line_dash="dash", line_color="red", annotation_text="Sell Zone (>70%)")
fig_pe_rank.update_layout(height=300, title="PE Rank (5 Year Rolling)")
st.plotly_chart(fig_pe_rank, use_container_width=True)


# 6. Backtest
st.markdown("---")
st.subheader("Strategy Backtest")

if st.button("🚀 Run Backtest (2018-Present)"):
    with st.spinner("Running Backtrader..."):
        # We need to capture stdout from run_backtest
        import io
        import sys
        import run_backtest

        # Capture output
        capture = io.StringIO()
        sys.stdout = capture

        try:
            # Reload strategy module to ensure params are fresh if we passed them (todo: pass params to run_backtest)
            # For now, run default
            run_backtest.run_backtest()
            output = capture.getvalue()
            st.text(output)
            st.success("Backtest Complete")
        except Exception as e:
            st.error(f"Backtest Failed: {e}")
        finally:
            sys.stdout = sys.__stdout__ # Restore
