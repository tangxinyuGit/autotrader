import backtrader as bt

# Define the custom data feed to include our pre-calculated signals
class ChiNextData(bt.feeds.PandasData):
    lines = ('pe_rank_5y', 'vol_ratio', 'bias_20', 'pe_ttm',)
    params = (
        ('pe_rank_5y', -1),
        ('vol_ratio', -1),
        ('bias_20', -1),
        ('pe_ttm', -1),
    )

class ChiNextStrategy(bt.Strategy):
    params = (
        ('buy_pe_threshold', 0.30),
        ('buy_vol_threshold', 0.60),
        ('grid_drop_pct', 0.05),
        ('sell_pe_threshold', 0.70),
        ('sell_bias_threshold', 0.15),
        ('position_step_pct', 0.30), # 30% of portfolio per trade
        ('max_position_pct', 0.90),  # Max 90%
    )

    def __init__(self):
        self.pe_rank = self.data.pe_rank_5y
        self.vol_ratio = self.data.vol_ratio
        self.bias = self.data.bias_20
        self.price = self.data.close
        # Add 60-day Moving Average for trend protection
        self.ma60 = bt.indicators.SMA(self.data.close, period=60)

        self.last_buy_price = None
        self.order = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.last_buy_price = order.executed.price
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.last_buy_price = None # Reset grid

            self.order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            self.order = None

    def next(self):
        if self.order:
            return

        # Portfolio Value
        port_value = self.broker.get_value()
        # Current Position Value
        pos_value = self.broker.getposition(self.data).size * self.price[0]
        # Current Position Percentage
        pos_pct = pos_value / port_value

        # --- SELL LOGIC ---
        # If we hold a position, check sell conditions
        if self.position:
            # Only sell if PE is high AND price is below MA60 (trend protection)
            if self.pe_rank[0] > self.params.sell_pe_threshold and self.price[0] < self.ma60[0]:
                self.log(f'SELL SIGNAL: Valuation Overheated AND Below MA60 (PE Rank: {self.pe_rank[0]:.2f}, Price: {self.price[0]:.2f}, MA60: {self.ma60[0]:.2f})')
                self.close()
                return

            if self.bias[0] > self.params.sell_bias_threshold:
                self.log(f'SELL SIGNAL: Sentiment Manic (Bias: {self.bias[0]:.2f})')
                self.close()
                return

        # --- BUY LOGIC ---
        # 1. Initial Entry
        if not self.position:
            if self.pe_rank[0] < self.params.buy_pe_threshold and self.vol_ratio[0] < self.params.buy_vol_threshold:
                # Check if valid data (sometimes rank is nan at start)
                if self.pe_rank[0] > 0:
                    self.log(f'BUY SIGNAL (Initial): PE Rank {self.pe_rank[0]:.2f}, Vol Ratio {self.vol_ratio[0]:.2f}')
                    self.buy_pct(target=self.params.position_step_pct)

        # 2. Grid Add-on
        else:
            # Check Max Position
            if pos_pct < self.params.max_position_pct - 0.01: # Buffer for float comparison
                if self.last_buy_price and self.price[0] < self.last_buy_price * (1 - self.params.grid_drop_pct):
                    self.log(f'BUY SIGNAL (Grid): Price {self.price[0]:.2f} < Last Buy {self.last_buy_price:.2f} * 0.95')
                    # Add another step.
                    # Note: order_target_percent sets TOTAL target.
                    # If current is 10%, we want 20%.
                    # But exact percent calculation is tricky with price moves.
                    # Simpler: Just buy 10% worth of CURRENT portfolio value.
                    self.buy(size=int((port_value * self.params.position_step_pct) / self.price[0]))

    def buy_pct(self, target):
         # Helper to buy target % of portfolio
         # Backtrader's order_target_percent targets the FINAL position size as % of portfolio
         # But here we want to ADD 10%.
         # Since we use it only for initial entry, target=0.10 is fine.
         self.order_target_percent(target=target)
