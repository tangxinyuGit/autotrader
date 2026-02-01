import run_backtest
import itertools

# Params to sweep
# Focused sweep to find a good config quickly
buy_vols = [0.6, 0.8, 1.0, 1.2, 1.5]
buy_pes = [0.30, 0.40]
macros = [True, False]
norths = [True, False]

best_sharpe = -999
best_params = {}
best_result = {}

print("Starting Optimization Loop...")

combinations = list(itertools.product(buy_vols, buy_pes, macros, norths))
total = len(combinations)
count = 0

for vol, pe, m, n in combinations:
    count += 1
    params = {
        'buy_vol_threshold': vol,
        'buy_pe_threshold': pe,
        'enable_macro_filter': m,
        'enable_northbound_filter': n
    }

    # print(f"[{count}/{total}] Testing {params}...")
    try:
        res = run_backtest.run_backtest(**params)
    except Exception as e:
        print(f"Error with {params}: {e}")
        continue

    if res['sharpe'] > best_sharpe:
        best_sharpe = res['sharpe']
        best_params = params
        best_result = res
        print(f"New Best: Sharpe {best_sharpe:.4f}, Return {res['return']:.2%}, Params: {params}")

print("\n=== Optimization Complete ===")
print(f"Best Sharpe: {best_sharpe:.4f}")
print(f"Best Return: {best_result.get('return', 0):.2%}")
print(f"Best Params: {best_params}")
