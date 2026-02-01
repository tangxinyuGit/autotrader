import backtrader as bt
import pandas as pd
import signal_calculator
from strategy import ChiNextStrategy, ChiNextData
import datetime

def run_backtest():
    # 1. Load Data
    print("Loading data and calculating signals...")
    df = signal_calculator.load_data()
    df = signal_calculator.calculate_signals(df)

    # Filter 2018-Present
    start_date = '2018-01-01'
    df = df[df.index >= pd.to_datetime(start_date)]

    if df.empty:
        print("No data for backtest.")
        return

    # 2. Setup Cerebro
    cerebro = bt.Cerebro()

    # 3. Add Feed
    data = ChiNextData(dataname=df)
    cerebro.adddata(data)

    # 4. Add Strategy
    # Note: Using 0.8 volume threshold for backtest demonstration as 0.6 is rarely met for Index
    cerebro.addstrategy(ChiNextStrategy, buy_vol_threshold=0.8)

    # 5. Set Cash
    cerebro.broker.setcash(1000000.0)
    cerebro.broker.setcommission(commission=0.0003) # Low commission for Index ETF/tracking

    # 6. Analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn') # For equity curve

    # 7. Run
    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    strat = results[0]

    print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")

    # 8. Report
    print("\n--- Backtest Report ---")

    # Sharpe
    sharpe = strat.analyzers.sharpe.get_analysis()
    print(f"Sharpe Ratio: {sharpe.get('sharperatio', 0):.4f}")

    # Drawdown
    dd = strat.analyzers.drawdown.get_analysis()
    print(f"Max Drawdown: {dd.max.drawdown:.2f}%")
    print(f"Max Drawdown Len: {dd.max.len} days")

    # Trades
    trades = strat.analyzers.trades.get_analysis()
    total_trades = trades.total.closed
    if total_trades > 0:
        win_rate = trades.won.total / total_trades
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Won: {trades.won.total}, Lost: {trades.lost.total}")
        print(f"Profit Factor: {trades.won.pnl.total / abs(trades.lost.pnl.total) if trades.lost.pnl.total != 0 else 'Inf':.2f}")
    else:
        print("No trades closed.")

    # Benchmark Comparison (Simple Buy & Hold)
    # Start Price
    start_price = df['close'].iloc[0]
    end_price = df['close'].iloc[-1]
    bench_return = (end_price - start_price) / start_price
    strat_return = (cerebro.broker.getvalue() - 1000000.0) / 1000000.0

    print(f"\nStrategy Return: {strat_return:.2%}")
    print(f"Benchmark Return (Buy & Hold): {bench_return:.2%}")

if __name__ == "__main__":
    run_backtest()
