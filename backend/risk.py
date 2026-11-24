"""Shortage risk for a store that lends a part, from real demand history.

Each part in the demo is tied to one series from the Monash Car Parts dataset: 51 months of
real monthly sales of one car part. The rule is deliberately simple so anyone can check it:

    risk = share of past months in which demand was MORE than what the store would have left

So a store holding 1 unit that lends it has 0 left, and its risk is the share of months with
any demand at all. This is an empirical frequency, not a forecast model.
"""
import functools
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSF = os.path.join(ROOT, "data", "car_parts_dataset_without_missing_values.tsf")
RISK_LIMIT = 0.30  # a lending store above this is marked unsafe


@functools.lru_cache(maxsize=1)
def _all_series():
    out, in_data = {}, False
    for line in open(TSF, encoding="latin-1"):
        line = line.strip()
        if line.lower() == "@data":
            in_data = True
            continue
        if in_data and line:
            name, _start, vals = line.split(":")
            out[name] = tuple(float(v) for v in vals.split(","))
    return out


def history(series_id):
    return _all_series().get(series_id, ())


def shortage_risk(series_id, left_after_lending):
    """Returns (risk between 0 and 1, months where demand exceeded what is left, months of history).
    The risk is None when the part has no demand history."""
    months = history(series_id)
    if not months:
        return None, 0, 0  # no history: the risk is unknown, which is not the same as safe
    over = sum(1 for d in months if d > left_after_lending)
    return over / len(months), over, len(months)
