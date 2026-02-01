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

    # Current values
    price = latest['close']
    pe_rank = latest['pe_rank_5y']
    vol_ratio = latest['vol_ratio']
    bias = latest['bias_20']

    # Strategy Params
    BUY_PE = 0.30
    BUY_VOL = 0.60
    SELL_PE = 0.70
    SELL_BIAS = 0.15
    GRID_DROP = 0.05
    MAX_POS = 3 # Max 3 units (30%)

    action = "HOLD"
    reason = "No signal"

    # --- LOGIC ---

    # Sell Logic
    if len(positions) > 0:
        if pe_rank > SELL_PE:
            action = "SELL"
            reason = f"Valuation Overheated (PE Rank {pe_rank:.2%})"
            # Reset state
            state["positions"] = []
            state["last_buy_price"] = None
        elif bias > SELL_BIAS:
            action = "SELL"
            reason = f"Sentiment Manic (Bias {bias:.2%})"
            state["positions"] = []
            state["last_buy_price"] = None

    # Buy Logic (if not selling)
    if action == "HOLD": # check buy
        # Initial Entry
        if len(positions) == 0:
            if pe_rank < BUY_PE and vol_ratio < BUY_VOL:
                action = "BUY (Initial)"
                reason = f"Cheap & Frozen (PE Rank {pe_rank:.2%}, VolRatio {vol_ratio:.2f})"
                state["positions"].append(price)
                state["last_buy_price"] = price
        # Grid Add
        elif len(positions) < MAX_POS:
            if last_buy_price and price < last_buy_price * (1 - GRID_DROP):
                action = "BUY (Grid)"
                reason = f"Price Drop (Price {price:.2f} < {last_buy_price:.2f} * 0.95)"
                state["positions"].append(price)
                state["last_buy_price"] = price

    # Save State
    if action != "HOLD":
        save_state(state)

    # 4. Notify
    msg = f"""
Date: {latest.name.date()}
Price: {price:.2f}
PE Rank: {pe_rank:.2%}
Vol Ratio: {vol_ratio:.2f}
Bias: {bias:.2%}
Positions: {len(positions)}/{MAX_POS}

Action: {action}
Reason: {reason}
    """

    notifier.notify(f"ChiNext Signal: {action}", msg)

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
