import json
import os

CONFIG_FILE = "strategy_config.json"

DEFAULT_CONFIG = {
    # Optimized Params (Sharpe 0.35, Return 77%)
    "buy_pe_threshold": 0.40,
    "buy_vol_threshold": 1.20,

    # Sell Params (Kept same)
    "sell_pe_threshold": 0.70,
    "sell_bias_threshold": 0.15,

    # Grid Params
    "grid_drop_pct": 0.05,
    "position_step_pct": 0.30,
    "max_position_pct": 0.90,

    # Filters
    "enable_macro_filter": True,      # Bond Yield Filter (Effective)
    "enable_northbound_filter": False # Northbound Filter (Reduced returns in backtest)
}

class StrategyConfig:
    def __init__(self):
        self.params = self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def save_config(self, new_params):
        self.params = {**self.params, **new_params}
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.params, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key):
        return self.params.get(key, DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.params[key] = value
        self.save_config({}) # Persist
