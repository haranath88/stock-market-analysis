#!/usr/bin/env python3
"""
Rolling 52-week consistency screener for NSE bhavcopy files.

Every time you run it, it looks at the LAST 52 COMPLETE WEEKS ending at your
latest bhavcopy file (weeks end Friday). It then:
  1. filters out penny, illiquid and low-delivery stocks
  2. splits the 52 weeks into 4-week blocks (13 blocks) and keeps stocks that
     gained at least --min-return % in EVERY block (strict mode)
  3. saves week-by-week returns for those stocks

Layout (default): keep this script in D:\\Stock Market Analysis with the bhavcopy
files in D:\\Stock Market Analysis\\Stock_History. Then just run:
  python consistent_gainers_52w.py
Other examples:
  python consistent_gainers_52w.py --mode avg        # looser rule
  python consistent_gainers_52w.py --weekly-all      # weekly table for all quality stocks
  python consistent_gainers_52w.py --folder "E:\\other\\bhav" --out-dir "E:\\other"

Outputs (saved next to the script; change with --out-dir):
  consistent_gainers_blocks.csv   4-week block returns + quality stats
  consistent_gainers_weekly.csv   weekly returns, e.g. W1 (1.2%), W2 (-2.0%), ...

Requires: pip install pandas
Reads old-style files (SYMBOL, SERIES, CLOSE_PRICE, DATE1, TTL_TRD_QNTY, DELIV_QTY,
DELIV_PER - e.g. sec_bhavdata_full) and the new UDiFF format (TckrSymb, SctySrs,
ClsPric, TradDt). .csv and .zip both work. Delivery filter needs delivery columns;
if they are absent it is skipped with a warning.
"""
import argparse
import glob
import io
import os
import sys
import zipfile

import pandas as pd

SYMBOL_COLS = ["SYMBOL", "TckrSymb"]
SERIES_COLS = ["SERIES", "SctySrs"]
CLOSE_COLS = ["CLOSE", "ClsPric", "CLOSE_PRICE"]
DATE_COLS = ["TIMESTAMP", "TradDt", "DATE1"]
VOLUME_COLS = ["TOTTRDQTY", "TtlTradgVol", "TTL_TRD_QNTY"]
DELIV_QTY_COLS = ["DELIV_QTY"]
DELIV_PER_COLS = ["DELIV_PER"]

OUTPUT_PREFIX = "consistent_gainers_"  # our own outputs are skipped when reading
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def pick(df, options):
    for c in options:
        if c in df.columns:
            return c
    return None


def num(df, col):
    if col is None:
        return float("nan")
    return pd.to_numeric(df[col], errors="coerce")  # '-' becomes NaN


def read_one(source, name):
    try:
        df = pd.read_csv(source, skipinitialspace=True)
    except Exception as e:
        print(f"  skipped {name}: {e}", file=sys.stderr)
        return None
    df.columns = [str(c).strip() for c in df.columns]
    sym, ser, cls, dt, vol = (pick(df, SYMBOL_COLS), pick(df, SERIES_COLS),
                              pick(df, CLOSE_COLS), pick(df, DATE_COLS),
                              pick(df, VOLUME_COLS))
    if not (sym and cls and dt):
        print(f"  skipped {name}: unrecognised columns", file=sys.stderr)
        return None
    return pd.DataFrame({
        "symbol": df[sym].astype(str).str.strip(),
        "series": df[ser].astype(str).str.strip() if ser else "EQ",
        "close": num(df, cls),
        "date": pd.to_datetime(df[dt].astype(str).str.strip(), errors="coerce", format="mixed"),
        "volume": num(df, vol),
        "deliv_qty": num(df, pick(df, DELIV_QTY_COLS)),
        "deliv_per": num(df, pick(df, DELIV_PER_COLS)),
    })


def load_all(folder):
    files = [f for f in glob.glob(os.path.join(folder, "**", "*"), recursive=True)
             if f.lower().endswith((".csv", ".zip"))
             and not os.path.basename(f).lower().startswith(OUTPUT_PREFIX)]
    if not files:
        sys.exit(f"No .csv or .zip files found under {folder}")
    frames = []
    for i, f in enumerate(sorted(files), 1):
        if f.lower().endswith(".zip"):
            with zipfile.ZipFile(f) as z:
                for member in z.namelist():
                    if member.lower().endswith(".csv"):
                        d = read_one(io.BytesIO(z.read(member)), member)
                        if d is not None:
                            frames.append(d)
        else:
            d = read_one(f, os.path.basename(f))
            if d is not None:
                frames.append(d)
        if i % 100 == 0:
            print(f"  read {i}/{len(files)} files...")
    if not frames:
        sys.exit("No usable data loaded.")
    df = pd.concat(frames, ignore_index=True)
    return df.dropna(subset=["date", "close"])


def fmt(p):
    return p.end_time.strftime("%d-%b-%y")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default=os.path.join(SCRIPT_DIR, "Stock_History"),
                    help="folder with bhavcopy files (default: Stock_History next to this script)")
    ap.add_argument("--out-dir", default=SCRIPT_DIR,
                    help="where to save outputs (default: the folder this script is in)")
    ap.add_argument("--weeks", type=int, default=52, help="size of the rolling window in weeks")
    ap.add_argument("--block-weeks", type=int, default=4,
                    help="weeks per block for the consistency rule (4 = roughly monthly)")
    ap.add_argument("--min-return", type=float, default=3.0, help="return needed per block, in %%")
    ap.add_argument("--mode", choices=["all", "avg"], default="all",
                    help="all: every block >= threshold; avg: average >= threshold and no negative block")
    ap.add_argument("--series", default="EQ", help="series to keep (default EQ)")
    ap.add_argument("--include-partial-week", action="store_true",
                    help="include the current week even if it has not finished")
    ap.add_argument("--as-of", default=None, help="treat this date (YYYY-MM-DD) as today; default: real today")
    # quality filters
    ap.add_argument("--min-price", type=float, default=50.0,
                    help="penny-stock filter: median close over the window must be >= this (Rs)")
    ap.add_argument("--min-avg-volume", type=float, default=100000, help="min average daily traded quantity")
    ap.add_argument("--min-avg-value-cr", type=float, default=2.0,
                    help="min average daily traded value in Rs crore")
    ap.add_argument("--min-delivery", type=float, default=35.0,
                    help="min average delivery %% (needs delivery columns in files)")
    ap.add_argument("--keep-flagged", action="store_true",
                    help="keep stocks with suspected split/bonus price jumps")
    ap.add_argument("--weekly-all", action="store_true",
                    help="weekly table for ALL stocks passing quality filters, not just winners")
    args = ap.parse_args()

    out_dir = args.out_dir or args.folder
    os.makedirs(out_dir, exist_ok=True)
    asof = pd.Timestamp(args.as_of) if args.as_of else pd.Timestamp.today().normalize()

    print("Loading bhavcopy files...")
    df = load_all(args.folder)
    df = df[df["series"].str.upper() == args.series.upper()]
    df = df.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")
    if df.empty:
        sys.exit(f"No rows for series {args.series}.")
    df["week"] = df["date"].dt.to_period("W-FRI")

    # ---------- find the rolling window ----------
    last_date = df["date"].max()
    last_week = df["week"].max()
    week_end = last_week.end_time.normalize()
    if not args.include_partial_week and last_date < week_end and asof <= week_end:
        df = df[df["week"] < last_week]
        last_week = last_week - 1
        print(f"Latest data ({last_date.date()}) is inside an unfinished week; "
              f"window ends at the week of {fmt(last_week)}. Use --include-partial-week to include it.")

    n = args.weeks
    cal = pd.period_range(end=last_week, periods=n + 1, freq="W-FRI")  # n+1 closes give n weekly returns
    df = df[df["week"].isin(cal)].copy()
    have = set(df["week"].unique())
    missing = [w for w in cal if w not in have]
    if cal[0] in missing:
        sys.exit(f"History too short: need data from the week ending {fmt(cal[0])} "
                 f"to cover {n} weeks. Your data starts later.")
    if missing:
        print(f"WARNING: no data at all for {len(missing)} week(s): "
              f"{', '.join(fmt(w) for w in missing[:6])}. Those weeks are skipped "
              f"(check for missing files).")
    present = [w for w in cal if w in have]
    baseline_end = cal[0].end_time.normalize()
    print(f"Window: {fmt(present[0])} (baseline) to {fmt(present[-1])}, {len(present) - 1} weekly returns.")

    df["value"] = df["close"] * df["volume"]

    # suspected split/bonus: huge one-day moves in unadjusted closes
    prev = df.groupby("symbol")["close"].shift(1)
    chg = df["close"] / prev - 1
    flagged = set(df.loc[(chg < -0.30) | (chg > 0.60), "symbol"])

    # ---------- quality filters over the window ----------
    win = df[df["date"] > baseline_end]
    q = win.groupby("symbol").agg(median_price=("close", "median"),
                                  avg_volume=("volume", "mean"),
                                  avg_value=("value", "mean"))
    q["avg_value_cr"] = q["avg_value"] / 1e7
    q = q.drop(columns="avg_value")

    has_delivery = win["deliv_qty"].notna().any() or win["deliv_per"].notna().any()
    if win["deliv_qty"].notna().any():
        w = win.dropna(subset=["deliv_qty"])
        s = w.groupby("symbol")[["deliv_qty", "volume"]].sum()
        q["avg_delivery_%"] = 100 * s["deliv_qty"] / s["volume"]
    elif win["deliv_per"].notna().any():
        q["avg_delivery_%"] = win.groupby("symbol")["deliv_per"].mean()
    else:
        print("WARNING: no delivery columns in your files, delivery filter skipped.")

    quality = (q["median_price"] >= args.min_price) & (q["avg_volume"] >= args.min_avg_volume) \
              & (q["avg_value_cr"] >= args.min_avg_value_cr)
    if has_delivery:
        quality &= q["avg_delivery_%"].fillna(0) >= args.min_delivery
    if not args.keep_flagged:
        quality &= ~q.index.isin(flagged)
    print(f"{int(quality.sum())} of {len(q)} stocks pass price/volume/value/delivery filters.")

    # ---------- weekly closes (stock must trade in every week) ----------
    wclose = df.groupby(["symbol", "week"])["close"].last().unstack("week").reindex(columns=present)
    wclose = wclose.dropna(how="any")

    # ---------- block rule (blocks aligned to the latest week) ----------
    m = len(present)
    idx = list(range(m - 1, -1, -args.block_weeks))[::-1]
    if len(idx) < 2:
        sys.exit("Window too short for the chosen --block-weeks.")
    blk = wclose.iloc[:, idx]
    bret = (blk / blk.shift(1, axis=1) - 1).iloc[:, 1:] * 100
    bret.columns = [f"B{i + 1} (to {fmt(present[j])})" for i, j in enumerate(idx[1:])]

    thr = args.min_return
    if args.mode == "all":
        passed = (bret >= thr).all(axis=1)
    else:
        passed = (bret.mean(axis=1) >= thr) & (bret >= 0).all(axis=1)

    bret = bret[bret.index.isin(q.index[quality])]
    passed = passed.reindex(bret.index)

    res = bret[passed].copy()
    res.insert(0, "avg_block_%", bret.mean(axis=1)[passed])
    res.insert(1, "min_block_%", bret.min(axis=1)[passed])
    qcols = ["median_price", "avg_volume", "avg_value_cr"] + (["avg_delivery_%"] if has_delivery else [])
    for i, c in enumerate(qcols):
        res.insert(2 + i, c, q.loc[res.index, c])
    res = res.sort_values("avg_block_%", ascending=False).round(2)
    blocks_path = os.path.join(out_dir, OUTPUT_PREFIX + "blocks.csv")
    res.to_csv(blocks_path)

    print(f"\nBlock rule ({args.mode}, >= {thr}% in each of {len(idx) - 1} blocks of "
          f"{args.block_weeks} weeks): {len(res)} stocks passed. Saved: {blocks_path}")
    if len(res):
        print(res[["avg_block_%", "min_block_%"] + qcols].head(25).to_string())
    else:
        print("None found. Try --mode avg, a lower --min-return, or relax the filters.")

    # ---------- weekly returns ----------
    targets = list(q.index[quality]) if args.weekly_all else list(res.index)
    targets = [t for t in targets if t in wclose.index]
    if targets:
        wsel = wclose.loc[targets]
        wret = (wsel / wsel.shift(1, axis=1) - 1).iloc[:, 1:] * 100
        wret.columns = [f"W{i + 1} ({fmt(w)})" for i, w in enumerate(present[1:])]
        out = pd.DataFrame(index=wret.index)
        out["weeks_up"] = (wret > 0).sum(axis=1)
        out["weeks_down"] = (wret < 0).sum(axis=1)
        out["avg_weekly_%"] = wret.mean(axis=1)
        out["worst_week_%"] = wret.min(axis=1)
        out["best_week_%"] = wret.max(axis=1)
        out["summary"] = [", ".join(f"W{i + 1} ({v:.1f}%)" for i, v in enumerate(row))
                          for row in wret.to_numpy()]
        out = pd.concat([out, wret], axis=1).sort_values("avg_weekly_%", ascending=False).round(2)
        weekly_path = os.path.join(out_dir, OUTPUT_PREFIX + "weekly.csv")
        out.to_csv(weekly_path)
        print(f"\nWeekly returns for {len(out)} stocks saved: {weekly_path}")
        print(f"Example: {out.index[0]} -> {out.iloc[0]['summary'][:110]}...")
    else:
        print("\nNo stocks for the weekly table.")

    print("\nNote: bhavcopy closes are not adjusted for splits/bonuses; "
          "stocks with suspicious jumps are excluded unless --keep-flagged is used.")


if __name__ == "__main__":
    main()
