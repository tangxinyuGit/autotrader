import backtrader as bt
from config import StrategyConfig
from decision_engine import DecisionEngine

# Define the custom data feed to include our pre-calculated signals
class ChiNextData(bt.feeds.PandasData):
    lines = ('pe_rank_5y', 'vol_ratio', 'bias_20', 'pe_ttm', 'ma60', 'bond_trend_down', 'north_inflow_20')
    params = (
        ('pe_rank_5y', -1),
        ('vol_ratio', -1),
        ('bias_20', -1),
        ('pe_ttm', -1),
        ('ma60', -1),
        ('bond_trend_down', -1),
        ('north_inflow_20', -1),
    )

class ChiNextStrategy(bt.Strategy):
    params = (
        ('buy_pe_threshold', 0.40),
        ('buy_vol_threshold', 1.20),
        ('grid_drop_pct', 0.05),
        ('sell_pe_threshold', 0.70),
        ('sell_bias_threshold', 0.15),
        ('position_step_pct', 0.30), # 30% of portfolio per trade
        ('max_position_pct', 0.90),  # Max 90%
        ('enable_macro_filter', True),
        ('enable_northbound_filter', False),
    )

    def __init__(self):
        # Initialize Config and Decision Engine
        self.config = StrategyConfig()
        # Override with params (allows optimization)
        for p in self.params._getkeys():
            self.config.set(p, getattr(self.params, p))

        self.engine = DecisionEngine(self.config)

        self.pe_rank = self.data.pe_rank_5y
        self.vol_ratio = self.data.vol_ratio
        self.bias = self.data.bias_20
        self.price = self.data.close
        # Use pre-calculated MA60 from data feed (consistency with live)
        self.ma60 = self.data.ma60
        self.bond_trend_down = self.data.bond_trend_down
        self.north_inflow = self.data.north_inflow_20

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

        # Prepare Data for Decision Engine
        data_dict = {
            'price': self.price[0],
            'pe_rank_5y': self.pe_rank[0],
            'vol_ratio': self.vol_ratio[0],
            'bias_20': self.bias[0],
            'ma60': self.ma60[0],
            'bond_trend_down': self.bond_trend_down[0],
            'north_inflow_20': self.north_inflow[0]
        }

        # Position Info
        has_pos = self.position.size > 0
        pos_count = 1 if has_pos else 0

        # Get Decision
        decision, reason = self.engine.analyze(data_dict, pos_count, self.last_buy_price)

        # Execute
        if decision == "SELL":
            self.log(f'SELL SIGNAL: {reason}')
            self.close()

        elif decision == "BUY_INITIAL":
            # Check if valid data (sometimes rank is nan at start)
            if self.pe_rank[0] > 0:
                self.log(f'BUY SIGNAL (Initial): {reason}')
                self.buy_pct(target=self.params.position_step_pct)

        elif decision == "BUY_GRID":
            # Check Max Position
            port_value = self.broker.get_value()
            pos_value = self.broker.getposition(self.data).size * self.price[0]
            pos_pct = pos_value / port_value

            if pos_pct < self.params.max_position_pct - 0.01:
                self.log(f'BUY SIGNAL (Grid): {reason}')
                self.buy(size=int((port_value * self.params.position_step_pct) / self.price[0]))

    def buy_pct(self, target):
         self.order_target_percent(target=target)
