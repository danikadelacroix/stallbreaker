"""Reproduce the simple-exponential-smoothing row of the Monash archive's Car Parts
results, then add intermittent-demand models (Croston family) on the same split.

Data: Monash Car Parts, 2,674 monthly series, Jan 1998 to Mar 2002, CC BY 4.0
      https://zenodo.org/records/4656021  (version without missing values)
Published table: https://forecastingdata.org/  (Car Parts, mean MASE: SES 0.897)

Setup used here (the Monash convention): last 12 months held out, MASE scaled by
the in-sample seasonal-naive error with a 12-month season, mean over series, and
forecasts rounded to whole units. Monash's own script passes integer conversion =
TRUE for car_parts:
https://github.com/rakshitha123/TSForecasting/blob/master/experiments/fixed_horizon.R

Run:  .venv/bin/python experiments/monash_baseline.py
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSF = os.path.join(ROOT, "data", "car_parts_dataset_without_missing_values.tsf")
OUT = os.path.join(ROOT, "experiments", "out")
HORIZON, SEASON = 12, 12


def load_tsf(path):
    series, in_data = {}, False
    for line in open(path, encoding="latin-1"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower() == "@data":
            in_data = True
            continue
        if in_data:
            name, _start, vals = line.split(":")
            series[name] = np.array([float(v) for v in vals.split(",")])
    return series


def mase(train, test, fc):
    scale = np.mean(np.abs(train[SEASON:] - train[:-SEASON]))
    return np.mean(np.abs(test - fc)) / scale if scale > 0 else np.nan


def main():
    from statsforecast import StatsForecast
    from statsforecast.models import (ADIDA, IMAPA, TSB, CrostonClassic, CrostonOptimized, CrostonSBA,
                                      HistoricAverage, Naive, SimpleExponentialSmoothingOptimized)
    series = load_tsf(TSF)
    n = len(series)
    length = {len(v) for v in series.values()}
    print(f"series: {n}, lengths: {sorted(length)}, share of zero months: "
          f"{np.mean(np.concatenate(list(series.values())) == 0):.1%}")
    rows = []
    for name, y in series.items():
        for t, v in enumerate(y[:-HORIZON]):
            rows.append((name, t + 1, v))
    df = pd.DataFrame(rows, columns=["unique_id", "ds", "y"])
    models = [SimpleExponentialSmoothingOptimized(alias="SES (optimised alpha only)"), Naive(), HistoricAverage(),
              CrostonClassic(), CrostonOptimized(), CrostonSBA(), ADIDA(), IMAPA(),
              TSB(alpha_d=0.2, alpha_p=0.2)]
    sf = StatsForecast(models=models, freq=1, n_jobs=1)
    fc = sf.forecast(df=df, h=HORIZON).reset_index(drop=False)
    cols = [c for c in fc.columns if c not in ("unique_id", "ds", "index")]
    from statsmodels.tsa.holtwinters import SimpleExpSmoothing
    R_SES = "SES (optimised alpha and start level, as in R)"
    res = {c: [] for c in cols + [R_SES, "Zero forecast"]}
    raw = {c: [] for c in cols + [R_SES, "Zero forecast"]}
    undefined = 0
    for name, g in fc.groupby("unique_id", sort=False):
        y = series[name]
        train, test = y[:-HORIZON], y[-HORIZON:]
        if not np.mean(np.abs(train[SEASON:] - train[:-SEASON])) > 0:
            undefined += 1
        f = {c: g[c].to_numpy() for c in cols}
        fit = SimpleExpSmoothing(train, initialization_method="estimated").fit()
        f[R_SES] = np.repeat(fit.forecast(1)[0], HORIZON)
        f["Zero forecast"] = np.zeros(HORIZON)
        for c, v in f.items():
            raw[c].append(mase(train, test, v))
            res[c].append(mase(train, test, np.round(v)))
    published = {R_SES: 0.897}
    lines = ["# Monash Car Parts: reproduced baseline and intermittent-demand models", "",
             f"{n} real monthly car-parts demand series, last {HORIZON} months held out, mean MASE "
             f"(12-month seasonal-naive scaling). {undefined} series have an undefined MASE (flat history) and are skipped.",
             "", "| Model | MASE, rounded to whole units (Monash setup) | Published (Monash) | MASE, not rounded |",
             "|---|---|---|---|"]
    for c in sorted(res, key=lambda c: np.nanmean(res[c])):
        pub = f"{published[c]:.3f}" if c in published else ""
        lines.append(f"| {c} | {np.nanmean(res[c]):.3f} | {pub} | {np.nanmean(raw[c]):.3f} |")
    lines += ["", "Reading: forecasting zero for every part every month scores best on this metric, because three "
              "quarters of all months have no demand. So this leaderboard metric cannot be used to decide whether "
              "a store can safely lend a part; that needs a stockout-risk measure instead."]
    text = "\n".join(lines)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "monash_baseline.md"), "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
