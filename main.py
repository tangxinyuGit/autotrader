import time
import schedule
import json
import os
import argparse
import pandas as pd
from datetime import datetime
import data_loader
import signal_calculator
import notifier
from config import StrategyConfig
from decision_engine import DecisionEngine

STATE_FILE = "trade_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"positions": [], "last_buy_price": None}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def job():
    print(f"\n[{datetime.now()}] Running Daily Job...")

    # 1. Update Data
    data_loader.update_database()

    # 2. Get Signals
    try:
        latest = signal_calculator.get_latest_signal()
    except Exception as e:
        notifier.notify("Error", f"Failed to calculate signals: {e}")
        return

    # 3. Load State
    state = load_state()
    positions = state.get("positions", [])
    last_buy_price = state.get("last_buy_price")

    # 4. Prepare Decision Engine
    config = StrategyConfig()
    engine = DecisionEngine(config)

    # Map Signals
    data_dict = {
        'price': latest['close'],
        'pe_rank_5y': latest['pe_rank_5y'],
        'vol_ratio': latest['vol_ratio'],
        'bias_20': latest['bias_20'],
        'ma60': latest['ma60'],
        'bond_trend_down': latest['bond_trend_down'],
        'north_inflow_20': latest['north_inflow_20']
    }

    # 5. Analyze
    decision, reason = engine.analyze(data_dict, len(positions), last_buy_price)

    action = "HOLD"

    # 6. Execute Logic (Mock)
    if decision == "SELL":
        action = "SELL"
        state["positions"] = []
        state["last_buy_price"] = None

    elif decision == "BUY_INITIAL":
        action = "BUY (Initial)"
        state["positions"].append(data_dict['price'])
        state["last_buy_price"] = data_dict['price']

    elif decision == "BUY_GRID":
        # Check max units (Simplification: 3 units max)
        if len(positions) < 3:
            action = "BUY (Grid)"
            state["positions"].append(data_dict['price'])
            state["last_buy_price"] = data_dict['price']
        else:
            action = "HOLD"
            reason = "Buy Signal (Grid) but Max Position Reached"

    # Save State
    if action != "HOLD":
        save_state(state)

    # Helper for display
    def fmt_bool(val):
        return "YES" if val else "NO"

    # 7. Notify
    msg = f"""
Date: {latest.name.date()}
Price: {data_dict['price']:.2f}
PE Rank: {data_dict['pe_rank_5y']:.2%}
Vol Ratio: {data_dict['vol_ratio']:.2f}
Bias: {data_dict['bias_20']:.2%}
Macro (Bond < MA60): {fmt_bool(data_dict['bond_trend_down'])}
Northbound (20d): {data_dict['north_inflow_20']:.2f}

Positions: {len(positions)}/3

Action: {action}
Reason: {reason}
    """

    notifier.notify(f"ChiNext Signal: {action}", msg)
    print(msg)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    if args.once:
        job()
    else:
        # Schedule daily at 15:30
        schedule.every().day.at("15:30").do(job)
        print("Scheduler started. Waiting for 15:30...")
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    main()
