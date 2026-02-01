import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import data_loader
import signal_calculator
from main import load_state
import json
import os
from config import StrategyConfig
from decision_engine import DecisionEngine

# Set Page Config
st.set_page_config(page_title="ChiNext 助手", layout="wide", page_icon="🤖")

# --- Helper Functions ---
@st.cache_data
def load_market_data():
    """Load data efficiently"""
    df = signal_calculator.load_data()
    df = signal_calculator.calculate_signals(df)
    return df

def update_config(key, value):
    config = StrategyConfig()
    config.set(key, value)
    config.save_config({})

# --- Sidebar ---
st.sidebar.title("🎛️ 策略控制台")

if st.sidebar.button("🔄 立即更新数据"):
    with st.spinner("正在连接 AkShare 更新数据..."):
        try:
            data_loader.update_database()
            st.cache_data.clear()
            st.success("数据已更新到最新！")
        except Exception as e:
            st.error(f"更新失败: {e}")

st.sidebar.markdown("---")
st.sidebar.header("参数设置")

# Instantiate Config
config = StrategyConfig()

# Inputs
buy_pe = st.sidebar.number_input(
    "买入估值水位 (PE Rank)", 0.0, 1.0, float(config.get('buy_pe_threshold')), step=0.05
)
if buy_pe != config.get('buy_pe_threshold'):
    update_config('buy_pe_threshold', buy_pe)

buy_vol = st.sidebar.number_input(
    "买入情绪水位 (Vol Ratio)", 0.0, 2.0, float(config.get('buy_vol_threshold')), step=0.1
)
if buy_vol != config.get('buy_vol_threshold'):
    update_config('buy_vol_threshold', buy_vol)

grid_drop = st.sidebar.number_input(
    "网格补仓跌幅", 0.0, 0.2, float(config.get('grid_drop_pct')), step=0.01
)
if grid_drop != config.get('grid_drop_pct'):
    update_config('grid_drop_pct', grid_drop)

st.sidebar.markdown("### 择时因子")
enable_macro = st.sidebar.checkbox("启用宏观择时 (国债收益率)", value=config.get('enable_macro_filter'))
if enable_macro != config.get('enable_macro_filter'):
    update_config('enable_macro_filter', enable_macro)

enable_nb = st.sidebar.checkbox("启用北向资金择时", value=config.get('enable_northbound_filter'))
if enable_nb != config.get('enable_northbound_filter'):
    update_config('enable_northbound_filter', enable_nb)


# --- Main Page ---
st.title("🤖 创业板指 (399006) 智能助理")

# 1. Load Data
try:
    df = load_market_data()
    latest = df.iloc[-1]
except Exception as e:
    st.warning("暂无数据，请点击左侧 '立即更新数据' 按钮。")
    st.stop()

# 2. State & Positions
state = load_state()
positions = state.get("positions", [])
last_buy_price = state.get("last_buy_price")

# 3. Decision Engine
st.markdown("### 📢 当前决策建议")

engine = DecisionEngine(config)
data_dict = {
    'price': latest['close'],
    'pe_rank_5y': latest['pe_rank_5y'],
    'vol_ratio': latest['vol_ratio'],
    'bias_20': latest['bias_20'],
    'ma60': latest['ma60'],
    'bond_trend_down': latest['bond_trend_down'],
    'north_inflow_20': latest['north_inflow_20']
}

decision, reason = engine.analyze(data_dict, len(positions), last_buy_price)

# Translate Decision to UI
status_color = "grey"
status_msg = "Unknown"
sub_msg = reason

if decision == "SELL":
    status_color = "red"
    status_msg = "🔴 卖出信号"
    sub_msg = f"建议清仓。原因: {reason}"
elif decision == "BUY_INITIAL":
    status_color = "green"
    status_msg = "🟢 建仓信号"
    sub_msg = f"建议首次买入 30%。原因: {reason}"
elif decision == "BUY_GRID":
    status_color = "red" # Alert
    status_msg = "🔴 补仓信号"
    sub_msg = f"建议网格加仓。原因: {reason}"
else: # HOLD
    if positions:
        status_color = "blue"
        status_msg = "🔵 持仓观望"
        sub_msg = f"持有 {len(positions)}/3 份。{reason}"
    else:
        status_color = "grey"
        status_msg = "☕ 空仓观望"
        sub_msg = f"未满足买入条件。{reason}"

# Display Banner
if status_color == "green":
    st.success(f"## {status_msg}\n{sub_msg}")
elif status_color == "red":
    st.error(f"## {status_msg}\n{sub_msg}")
elif status_color == "blue":
    st.info(f"## {status_msg}\n{sub_msg}")
else:
    st.warning(f"## {status_msg}\n{sub_msg}")

# 4. Metrics Row
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("当前点位", f"{latest['close']:.2f}", f"{latest['close'] - df.iloc[-2]['close']:.2f}")
with col2:
    st.metric("估值水位", f"{latest['pe_rank_5y']:.1%}", delta=f"目标 < {buy_pe:.0%}", delta_color="inverse")
with col3:
    st.metric("情绪水位", f"{latest['vol_ratio']:.2f}", delta=f"目标 < {buy_vol:.2f}", delta_color="inverse")
with col4:
    st.metric("宏观/北向",
              f"{'📉顺势' if latest['bond_trend_down'] else '📈逆势'} / {'💰流入' if latest['north_inflow_20']>0 else '💸流出'}",
              help="宏观: 国债收益率趋势; 北向: 20日净流入")

# 5. Charts
st.subheader("📊 市场趋势与信号")
tab1, tab2 = st.tabs(["价格与网格", "估值历史"])

with tab1:
    fig_price = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig_price.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K线'), row=1, col=1)
    fig_price.add_trace(go.Scatter(x=df.index, y=df['ma20'], line=dict(color='orange', width=1), name='20日线'), row=1, col=1)
    
    if positions and last_buy_price:
        next_grid = last_buy_price * (1 - grid_drop)
        fig_price.add_hline(y=next_grid, line_dash="dash", line_color="red", annotation_text="补仓线")

    fig_price.add_trace(go.Bar(x=df.index, y=df['volume'], name='成交量'), row=2, col=1)
    fig_price.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_price, use_container_width=True) # Fixed warning

with tab2:
    fig_pe = go.Figure()
    fig_pe.add_trace(go.Scatter(x=df.index, y=df['pe_rank_5y'], name='PE分位', fill='tozeroy', line=dict(color='#3b82f6')))
    fig_pe.add_hline(y=buy_pe, line_dash="dash", line_color="green", annotation_text=f"买入线 ({buy_pe:.0%})")
    fig_pe.add_hline(y=config.get('sell_pe_threshold'), line_dash="dash", line_color="red", annotation_text="卖出线")
    fig_pe.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_pe, use_container_width=True) # Fixed warning

# 6. Backtest
st.markdown("---")
with st.expander("🛠️ 策略回测实验室 (点击展开)"):
    st.write("测试当前配置的策略表现：")
    if st.button("🚀 运行回测"):
        with st.spinner("正在模拟交易..."):
            import io
            import sys
            import run_backtest

            # Since we updated config via sidebar, run_backtest will pick it up via StrategyConfig!
            # BUT run_backtest currently passes `buy_vol_threshold=0.8`.
            # We should modify run_backtest.py to NOT override params if we want to test dashboard config.
            # OR we instruct user that dashboard controls the config.

            capture = io.StringIO()
            sys.stdout = capture
            try:
                # We need to ensure run_backtest uses the config file values
                # Currently run_backtest.py has hardcoded override.
                # I should probably update run_backtest.py in Step 4 to respect config file if no args provided.
                run_backtest.run_backtest()
                output = capture.getvalue()
                st.code(output, language='text')
            except Exception as e:
                st.error(f"回测出错: {e}")
            finally:
                sys.stdout = sys.__stdout__
