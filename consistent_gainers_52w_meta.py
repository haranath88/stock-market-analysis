import os
import glob
import argparse
import pandas as pd
import numpy as np
import itertools

parser = argparse.ArgumentParser(description="52W Consistent Gainers with Pattern Detection")
parser.add_argument('--data-dir', type=str, default=r"D:\Stock Market Analysis\Stock_History", help="Folder with daily NSE bhavcopy CSVs")
parser.add_argument('--min-price', type=float, default=100, help="Min median and last price")
parser.add_argument('--min-avg-volume', type=float, default=300000, help="Min avg daily volume")
parser.add_argument('--min-avg-value-cr', type=float, default=10, help="Min avg daily value in Cr")
parser.add_argument('--min-delivery', type=float, default=40, help="Min avg delivery percent")
parser.add_argument('--min-days', type=int, default=300, help="Min trading days")
parser.add_argument('--weeks', type=int, default=52, help="Last N weeks")
args = parser.parse_args()

files = glob.glob(os.path.join(args.data_dir, "*.csv"))
print(f"Found {len(files)} files in {args.data_dir}")

all_chunks = []
for f in files:
    try:
        df = pd.read_csv(f, low_memory=False)
        df.columns = [c.strip().upper() for c in df.columns]
        if 'SYMBOL' not in df.columns or 'DATE1' not in df.columns or 'CLOSE_PRICE' not in df.columns:
            continue
        if 'SERIES' in df.columns:
            df = df[df['SERIES'].astype(str).str.strip() == 'EQ']
            if len(df) == 0:
                continue
        df['SYMBOL'] = df['SYMBOL'].astype(str).str.strip().str.upper()
        df['DATE'] = pd.to_datetime(df['DATE1'].astype(str).str.strip(), format='%d-%b-%Y', errors='coerce')
        df['CLOSE'] = pd.to_numeric(df['CLOSE_PRICE'].astype(str).str.strip(), errors='coerce')
        df['VOL'] = pd.to_numeric(df['TTL_TRD_QNTY'].astype(str).str.strip(), errors='coerce') if 'TTL_TRD_QNTY' in df.columns else np.nan
        df['DELIV_PER'] = pd.to_numeric(df['DELIV_PER'].astype(str).str.strip(), errors='coerce') if 'DELIV_PER' in df.columns else np.nan
        df['TURNOVER'] = pd.to_numeric(df['TURNOVER_LACS'].astype(str).str.strip(), errors='coerce') if 'TURNOVER_LACS' in df.columns else df['CLOSE'] * df['VOL'] / 100000
        df = df.dropna(subset=['DATE', 'CLOSE', 'SYMBOL'])
        if len(df) > 0:
            all_chunks.append(df[['DATE', 'SYMBOL', 'CLOSE', 'VOL', 'DELIV_PER', 'TURNOVER']])
    except:
        continue

if not all_chunks:
    print("No valid data found")
    exit(1)

daily_full = pd.concat(all_chunks, ignore_index=True).sort_values('DATE')
print(f"Loaded {len(daily_full)} trades | {daily_full['SYMBOL'].nunique()} symbols")

dclose = daily_full.pivot_table(index='DATE', columns='SYMBOL', values='CLOSE', aggfunc='last').sort_index()
dvol = daily_full.pivot_table(index='DATE', columns='SYMBOL', values='VOL', aggfunc='mean').sort_index()
dturn = daily_full.pivot_table(index='DATE', columns='SYMBOL', values='TURNOVER', aggfunc='mean').sort_index()
ddeliv = daily_full.pivot_table(index='DATE', columns='SYMBOL', values='DELIV_PER', aggfunc='mean').sort_index()

q = pd.DataFrame(index=dclose.columns)
q['trading_days'] = dclose.count()
q['last_price'] = dclose.ffill().iloc[-1]
q['median_price'] = dclose.median()
q['avg_volume'] = dvol.mean()
q['avg_value_cr'] = dturn.mean() / 100
q['avg_delivery'] = ddeliv.mean()

print(f"\nBefore filter: {len(q)} stocks")
quality = (
    (q['median_price'] >= args.min_price) &
    (q['last_price'] >= args.min_price) &
    (q['avg_volume'] >= args.min_avg_volume) &
    (q['avg_value_cr'] >= args.min_avg_value_cr) &
    (q['avg_delivery'] >= args.min_delivery) &
    (q['trading_days'] >= args.min_days)
)
q_pass = q[quality].copy()
print(f"After filter: {len(q_pass)} PASS | Dropped {len(q)-len(q_pass)}")

if len(q_pass) == 0:
    exit(1)

# Intra-week logic: daily pct then weekly avg
dclose_f = dclose[list(q_pass.index)]
daily_pct = dclose_f.pct_change() * 100
weekly_avg = daily_pct.resample('W-FRI').mean()
wclose = weekly_avg.tail(args.weeks)

print(f"Weekly: {wclose.shape[0]} weeks x {wclose.shape[1]} stocks")

# Weekly stats
weekly_stats = pd.DataFrame(index=wclose.columns)
weekly_stats['avg_weekly_pct'] = wclose.mean()
weekly_stats['weeks_up'] = (wclose > 0).sum()
weekly_stats['weeks_down'] = (wclose < 0).sum()
weekly_stats['best_week'] = wclose.max()
weekly_stats['worst_week'] = wclose.min()

# Pattern detection
def analyze_patterns(wclose_df):
    rows = []
    for sym in wclose_df.columns:
        s = wclose_df[sym].dropna()
        if len(s) < 20:
            continue
        autocorr = s.autocorr(lag=1) if len(s) > 5 else 0
        win_rate = (s > 0).mean() * 100
        is_up = (s > 0).astype(int).tolist()
        # longest streaks
        max_up = max_down = cur_up = cur_down = 0
        tmp_up = tmp_down = 0
        for v in is_up:
            if v == 1:
                tmp_up += 1
                tmp_down = 0
                max_up = max(max_up, tmp_up)
            else:
                tmp_down += 1
                tmp_up = 0
                max_down = max(max_down, tmp_down)
        # alternating triplets
        signs = np.sign(s).values
        triple_alt = 0
        for i in range(len(signs)-2):
            if signs[i] != 0 and signs[i+1] != 0 and signs[i+2] != 0:
                if signs[i] != signs[i+1] and signs[i+1] != signs[i+2]:
                    triple_alt += 1
        triple_alt_pct = triple_alt / max(len(s)-2,1) * 100
        change_pct = (s.diff().apply(lambda x: 1 if x!=0 else 0).sum()) / len(s) * 100
        
        if autocorr < -0.25 and triple_alt_pct > 35:
            pat = "PROFIT_BOOKING"
        elif autocorr > 0.25:
            pat = "MOMENTUM"
        elif win_rate >= 60:
            pat = "CONSISTENT_UP"
        elif win_rate <= 40:
            pat = "CONSISTENT_DOWN"
        else:
            pat = "RANDOM"
        rows.append([sym, round(autocorr,3), round(win_rate,1), max_up, max_down, round(triple_alt_pct,1), pat])
    return pd.DataFrame(rows, columns=['SYMBOL','autocorr_L1','win_rate','longest_up','longest_down','alt_triplet_pct','PATTERN'])

pattern_df = analyze_patterns(wclose)
print("\nPattern counts:")
print(pattern_df['PATTERN'].value_counts().to_string())

# Weekly table with dates
weekly_cols = [f"W{i+1}_{d.strftime('%d%b')}" for i, d in enumerate(wclose.index)]
weekly_table = wclose.T
weekly_table.columns = weekly_cols

# Final merge
final = pd.concat([weekly_stats, q_pass], axis=1)
final = final.merge(pattern_df.set_index('SYMBOL'), left_index=True, right_index=True, how='left')
final = pd.concat([final, weekly_table], axis=1).sort_values('avg_weekly_pct', ascending=False)

final.to_csv('consistent_gainers_weekly.csv', index=True)
pattern_df.to_csv('pattern_summary.csv', index=False)

print(f"\nSAVED:")
print(f"  consistent_gainers_weekly.csv - {len(final)} stocks with full weekly pct + patterns")
print(f"  pattern_summary.csv - quick pattern list")
print(f"\n--- TOP Profit Booking (your example) ---")
print(pattern_df[pattern_df['PATTERN']=='PROFIT_BOOKING'].sort_values('alt_triplet_pct', ascending=False).head(10).to_string(index=False))