import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import data_loader
import signal_calculator
from main import load_state # Fixed import error
import json
import os

# Set Page Config
st.set_page_config(page_title="ChiNext 助手", layout="wide", page_icon="🤖")

# --- Helper Functions ---
@st.cache_data
def load_market_data():
    """Load data efficiently"""
    df = signal_calculator.load_data()
    df = signal_calculator.calculate_signals(df)
    return df

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
buy_pe = st.sidebar.number_input("买入估值水位 (PE Rank)", 0.0, 1.0, 0.30, help="低于这个百分位才开始考虑买入")
buy_vol = st.sidebar.number_input("买入情绪水位 (Vol Ratio)", 0.0, 2.0, 0.60, help="成交量萎缩到这个比例才买")
grid_drop = st.sidebar.number_input("网格补仓跌幅", 0.0, 0.2, 0.05, help="每跌多少补一次仓")

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

# 3. 核心决策区 (Human Language Zone)
st.markdown("### 📢 当前决策建议")

# Logic to generate human message
status_color = "grey"
status_msg = "获取中..."
sub_msg = ""

# Current Metrics
cur_pe_rank = latest['pe_rank_5y']
cur_vol = latest['vol_ratio']
cur_price = latest['close']

if positions:
    # Holding State
    status_color = "blue"
    status_msg = f"🔵 持仓中 (成本保护模式)"
    profit = (cur_price - positions[-1]) / positions[-1]
    sub_msg = f"当前持有 {len(positions)}/3 份。最新一笔浮动盈亏: {profit:.2%}"
    
    if last_buy_price:
        next_buy = last_buy_price * (1 - grid_drop)
        if cur_price < next_buy:
             status_color = "red"
             status_msg = "🔴 触发补仓信号！"
             sub_msg = f"价格 ({cur_price:.2f}) 已跌破补仓线 ({next_buy:.2f})，建议执行买入。"
        else:
             sub_msg += f" | 等待下跌至 {next_buy:.2f} 补仓"

else:
    # Empty State
    if cur_pe_rank < buy_pe and cur_vol < buy_vol:
        status_color = "green"
        status_msg = "🟢 黄金坑！建议买入"
        sub_msg = f"估值便宜 (Rank {cur_pe_rank:.0%}) 且 情绪冰点 (Vol {cur_vol:.2f})，满足建仓条件。"
    elif cur_pe_rank < buy_pe:
        status_color = "orange"
        status_msg = "🟡 估值够低，但不够恐慌"
        sub_msg = f"估值已进入低位 ({cur_pe_rank:.0%})，但成交量 ({cur_vol:.2f}) 还未萎缩到极致，建议再等等或小额定投。"
    else:
        status_color = "grey"
        status_msg = "☕ 空仓观望 (太贵了)"
        sub_msg = f"当前估值分位 {cur_pe_rank:.0%} (高于设定的 {buy_pe:.0%})，没有安全边际。请耐心等待机会。"

# Display the banner
if status_color == "green":
    st.success(f"## {status_msg}\n{sub_msg}")
elif status_color == "red":
    st.error(f"## {status_msg}\n{sub_msg}")
elif status_color == "blue":
    st.info(f"## {status_msg}\n{sub_msg}")
elif status_color == "orange":
    st.warning(f"## {status_msg}\n{sub_msg}")
else:
    st.info(f"## {status_msg}\n{sub_msg}")


# 4. Metrics Row
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("当前点位", f"{latest['close']:.2f}", f"{latest['close'] - df.iloc[-2]['close']:.2f}")
with col2:
    st.metric("估值水位 (PE Rank)", f"{latest['pe_rank_5y']:.1%}", delta=f"距离买点还差 {(latest['pe_rank_5y']-buy_pe)*100:.1f}%", delta_color="inverse")
with col3:
    st.metric("情绪水位 (Vol Ratio)", f"{latest['vol_ratio']:.2f}", delta=f"距离冰点还差 {latest['vol_ratio']-buy_vol:.2f}", delta_color="inverse")
with col4:
    st.metric("持仓状态", f"{len(positions)} / 3 份", f"上次买入: {last_buy_price if last_buy_price else '无'}")

# 5. Charts
st.subheader("📊 市场趋势与信号")
tab1, tab2 = st.tabs(["价格与网格", "估值历史"])

with tab1:
    # Chart 1: Price
    fig_price = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    # Candle
    fig_price.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K线'), row=1, col=1)
    # MA20
    fig_price.add_trace(go.Scatter(x=df.index, y=df['ma20'], line=dict(color='orange', width=1), name='20日线'), row=1, col=1)
    
    # Grid Line
    if positions and last_buy_price:
        next_grid = last_buy_price * (1 - grid_drop)
        fig_price.add_hline(y=next_grid, line_dash="dash", line_color="red", annotation_text="补仓线")

    # Vol
    fig_price.add_trace(go.Bar(x=df.index, y=df['volume'], name='成交量'), row=2, col=1)
    fig_price.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_price, use_container_width='stretch')

with tab2:
    # Chart 2: PE Rank
    fig_pe = go.Figure()
    fig_pe.add_trace(go.Scatter(x=df.index, y=df['pe_rank_5y'], name='PE分位', fill='tozeroy', line=dict(color='#3b82f6')))
    fig_pe.add_hline(y=buy_pe, line_dash="dash", line_color="green", annotation_text=f"买入线 ({buy_pe:.0%})")
    fig_pe.add_hline(y=0.7, line_dash="dash", line_color="red", annotation_text="卖出线 (70%)")
    fig_pe.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_pe, use_container_width='stretch')

# 6. Backtest
st.markdown("---")
with st.expander("🛠️ 策略回测实验室 (点击展开)"):
    st.write("测试这套策略在过去几年的表现：")
    if st.button("🚀 运行回测"):
        with st.spinner("正在模拟交易..."):
            import io
            import sys
            import run_backtest
            capture = io.StringIO()
            sys.stdout = capture
            try:
                run_backtest.run_backtest()
                output = capture.getvalue()
                st.code(output, language='text')
            except Exception as e:
                st.error(f"回测出错: {e}")
            finally:
                sys.stdout = sys.__stdout__