import backtrader as bt
import pandas as pd
import signal_calculator
from strategy import ChiNextStrategy, ChiNextData
import datetime

def run_backtest(**kwargs):
    # 1. Load Data
    # print("Loading data and calculating signals...")
    df = signal_calculator.load_data()
    df = signal_calculator.calculate_signals(df)

    # Filter 2018-Present
    start_date = '2018-01-01'
    df = df[df.index >= pd.to_datetime(start_date)]

    if df.empty:
        print("No data for backtest.")
        return None

    # 2. Setup Cerebro
    cerebro = bt.Cerebro()

    # 3. Add Feed
    data = ChiNextData(dataname=df)
    cerebro.adddata(data)

    # 4. Add Strategy
    # Pass kwargs to strategy. If kwargs empty, strategy uses its own defaults (or config).
    cerebro.addstrategy(ChiNextStrategy, **kwargs)

    # 5. Set Cash
    cerebro.broker.setcash(1000000.0)
    cerebro.broker.setcommission(commission=0.0003) # Low commission for Index ETF/tracking

    # 6. Analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')

    # 7. Run
    results = cerebro.run()
    strat = results[0]

    # 8. Report
    # Sharpe
    sharpe_dict = strat.analyzers.sharpe.get_analysis()
    sharpe = sharpe_dict.get('sharperatio', 0)
    if sharpe is None: sharpe = -999 # Handle None

    # Drawdown
    dd = strat.analyzers.drawdown.get_analysis()
    max_dd = dd.max.drawdown

    # Returns
    strat_return = (cerebro.broker.getvalue() - 1000000.0) / 1000000.0

    # Print only if running as main
    if __name__ == "__main__":
        print(f"Sharpe: {sharpe:.4f}")
        print(f"Return: {strat_return:.2%}")
        print(f"Max DD: {max_dd:.2f}%")

    return {
        'sharpe': sharpe,
        'return': strat_return,
        'drawdown': max_dd
    }

if __name__ == "__main__":
    # Run with defaults (from config.py)
    run_backtest()
