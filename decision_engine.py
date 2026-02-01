from config import StrategyConfig

class DecisionEngine:
    def __init__(self, config: StrategyConfig):
        self.config = config

    def analyze(self, data, position_count, last_buy_price=None):
        """
        Analyzes market data and returns a trading decision.

        Args:
            data (dict): Contains market signals:
                - price (float)
                - pe_rank_5y (float)
                - vol_ratio (float)
                - bias_20 (float)
                - ma60 (float)
                - bond_trend_down (bool/int)
                - north_inflow_20 (float)
            position_count (int): Current number of position units/layers held.
            last_buy_price (float, optional): Price of the last buy execution.

        Returns:
            tuple: (action, reason)
                action: "BUY_INITIAL", "BUY_GRID", "SELL", "HOLD"
                reason: Description of the decision.
        """

        # Unpack Data
        price = data.get('price')
        pe_rank = data.get('pe_rank_5y')
        vol_ratio = data.get('vol_ratio')
        bias = data.get('bias_20')
        ma60 = data.get('ma60')
        bond_trend_down = data.get('bond_trend_down')
        north_inflow = data.get('north_inflow_20')

        # Safe Defaults if data is missing (e.g. NaN)
        if price is None or pe_rank != pe_rank: # NaN check
            return "HOLD", "Invalid Data"

        # Config
        buy_pe = self.config.get('buy_pe_threshold')
        buy_vol = self.config.get('buy_vol_threshold')
        sell_pe = self.config.get('sell_pe_threshold')
        sell_bias = self.config.get('sell_bias_threshold')
        grid_drop = self.config.get('grid_drop_pct')

        has_position = position_count > 0

        # --- SELL LOGIC ---
        if has_position:
            # 1. Valuation Overheated
            # Logic: Sell if PE is high AND Trend is broken (Price < MA60)
            if pe_rank > sell_pe:
                 if ma60 and price < ma60:
                     return "SELL", f"Valuation Overheated (PE Rank {pe_rank:.2%}) & Broken Trend (< MA60)"

            # 2. Sentiment Manic
            if bias > sell_bias:
                return "SELL", f"Sentiment Manic (Bias {bias:.2%})"

        # --- BUY LOGIC ---
        # 1. Initial Entry
        if not has_position:
            # Base Conditions
            if pe_rank < buy_pe and vol_ratio < buy_vol:

                # Check Macro Filter (if enabled)
                if self.config.get('enable_macro_filter'):
                    # bond_trend_down might be 1/0 or True/False.
                    if not bond_trend_down:
                        return "HOLD", "Macro Filter: Bond Yield not trending down"

                # Check Northbound Filter (if enabled)
                if self.config.get('enable_northbound_filter'):
                    # Northbound inflow > 0 means foreign capital is entering
                    if north_inflow is not None and north_inflow <= 0:
                         return "HOLD", f"Northbound Filter: Net Outflow ({north_inflow:.2f})"

                return "BUY_INITIAL", f"Initial Entry: Cheap (PE {pe_rank:.2%}) & Frozen (Vol {vol_ratio:.2f})"

        # 2. Grid Add-on
        else:
            if last_buy_price and price < last_buy_price * (1 - grid_drop):
                 return "BUY_GRID", f"Grid Add: Price drop {grid_drop:.1%} (Current {price:.2f} < Last {last_buy_price:.2f})"

        return "HOLD", "No Signal"
