import pandas as pd
import numpy as np

print("Loading consistent_gainers_weekly.csv ...")
df = pd.read_csv('consistent_gainers_weekly.csv', index_col=0)

# Find weekly columns W1_... W52_...
wcols = [c for c in df.columns if c.startswith('W') and '_' in c]
if len(wcols) == 0:
    wcols = [c for c in df.columns if c.startswith('W')]
wcols = sorted(wcols, key=lambda x: int(x.split('_')[0][1:]))  # Jan to Oct

print(f"Found {len(wcols)} weekly columns: {wcols[0]} to {wcols[-1]}")
print(f"Total stocks: {len(df)}")

# Backtest: YTD Jan to Oct 2026
df['cum_sum'] = df[wcols].sum(axis=1)
df['cum_comp'] = (1 + df[wcols]/100).prod(axis=1) - 1
df['cum_comp_pct'] = df['cum_comp'] * 100

# Ensure required columns exist
for col in ['PATTERN','longest_down','best_week','worst_week','avg_delivery','avg_weekly_pct']:
    if col not in df.columns:
        df[col] = 0

# 7 FILTERS
filters = {
    '1_PROFIT_BOOKING': df[df['PATTERN'] == 'PROFIT_BOOKING'],
    '2_MOMENTUM': df[df['PATTERN'] == 'MOMENTUM'],
    '3_CONSISTENT_UP': df[df['PATTERN'] == 'CONSISTENT_UP'],
    '4_CONSISTENT_DOWN': df[df['PATTERN'] == 'CONSISTENT_DOWN'],
    '5_BURST': df[(df['longest_down'] >= 2) & (df['best_week'] > 4)],
    '6_STABLE': df[(df['worst_week'] > -3) & (df['avg_delivery'] > 50) & (df['avg_weekly_pct'] > 0)],
    '7_TOP50_GAINERS': df.nlargest(50, 'avg_weekly_pct')
}

summary = []
for name, g in filters.items():
    if len(g) == 0:
        print(f"{name}: 0 stocks - skipped")
        continue
    g_sorted = g.sort_values('cum_comp_pct', ascending=False)
    # Save full data with all weekly columns + backtest
    g_sorted.to_csv(f'{name}.csv')
    avg_comp = g_sorted['cum_comp_pct'].mean()
    win_pct = (g_sorted['cum_comp_pct'] > 0).mean() * 100
    summary.append([name, len(g_sorted), round(avg_comp, 2), round(win_pct, 1)])
    print(f"Saved {name}.csv -> {len(g_sorted)} stocks | YTD Avg {avg_comp:.2f}% | Win {win_pct:.0f}%")

# Summary CSV
summary_df = pd.DataFrame(summary, columns=['FILTER','COUNT','AVG_YTD_COMP_PCT','WIN_PCT'])
summary_df.to_csv('backtest_summary_7_filters.csv', index=False)
print("\n=== SUMMARY ===")
print(summary_df.to_string(index=False))
print("\nAll 7 files created in current folder!")

# Optional: Chart
try:
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10,5))
    plt.bar(summary_df['FILTER'], summary_df['AVG_YTD_COMP_PCT'])
    plt.xticks(rotation=20)
    plt.ylabel('Avg YTD % (Jan-Oct 2026)')
    plt.title('Backtest by Filter - 2026 YTD Till Date')
    plt.tight_layout()
    plt.savefig('backtest_chart.png')
    print("Saved backtest_chart.png")
except:
    pass