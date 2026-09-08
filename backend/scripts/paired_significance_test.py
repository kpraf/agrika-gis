"""
paired_significance_test.py
===========================

Objective 1 significance test: is the Enhanced (S2+S1) model's improvement over
the Original (S2-only) model statistically real, or within noise?

Follows the plan in the revision list:
  1. Shapiro-Wilk normality test on the paired differences of absolute error.
  2. If normal  -> paired t-test (ttest_rel).
     If not     -> Wilcoxon signed-rank test.
Both are reported for transparency; the Shapiro result decides the primary one.

Paired on the SAME test observations (leave-one-year-out OOF predictions), so
each sample contributes one (original_error, enhanced_error) pair.

diff = |err_original| - |err_enhanced|   (positive => enhanced is better)

Requires: pandas, scipy. Reads db/cnn_lstm_oof_predictions.csv.

Usage
    python backend/scripts/paired_significance_test.py
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
OOF_CSV = os.path.join(DB_DIR, "cnn_lstm_oof_predictions.csv")


def main():
    df = pd.read_csv(OOF_CSV)
    e_orig = df["abserr_s2_only"].to_numpy()
    e_enh = df["abserr_s2_s1"].to_numpy()
    diff = e_orig - e_enh  # positive => enhanced has smaller error

    n = len(diff)
    print(f"paired samples: {n}")
    print(f"mean |error|  original (S2)   : {e_orig.mean():.4f}")
    print(f"mean |error|  enhanced (S2+S1): {e_enh.mean():.4f}")
    print(f"mean improvement (orig - enh) : {diff.mean():+.4f} t/ha "
          f"({100*diff.mean()/e_orig.mean():+.1f}% of original error)")
    better = int((diff > 0).sum())
    print(f"samples where enhanced is better: {better}/{n} ({100*better/n:.1f}%)\n")

    # 1. Normality of the paired differences
    sw_stat, sw_p = stats.shapiro(diff)
    normal = sw_p > 0.05
    print(f"Shapiro-Wilk on differences: W={sw_stat:.4f}, p={sw_p:.4g} "
          f"-> {'normal' if normal else 'NOT normal'} (alpha=0.05)")

    # 2. Both tests, two-sided
    t_stat, t_p = stats.ttest_rel(e_orig, e_enh)
    try:
        w_stat, w_p = stats.wilcoxon(e_orig, e_enh)
    except ValueError as e:  # e.g. all-zero differences
        w_stat, w_p = float("nan"), float("nan")
        print(f"(Wilcoxon note: {e})")

    print(f"\nPaired t-test        : t={t_stat:.4f}, p={t_p:.4g}")
    print(f"Wilcoxon signed-rank : W={w_stat:.4f}, p={w_p:.4g}")

    primary_name = "paired t-test" if normal else "Wilcoxon signed-rank"
    primary_p = t_p if normal else w_p
    print(f"\nPRIMARY (per Shapiro-Wilk): {primary_name}, p={primary_p:.4g}")

    # Effect size: Cohen's d for paired samples
    d = diff.mean() / diff.std(ddof=1) if diff.std(ddof=1) > 0 else float("nan")
    print(f"Effect size (Cohen's d, paired): {d:.3f}")

    sig = primary_p < 0.05
    direction = "enhanced (S2+S1) is better" if diff.mean() > 0 else "original (S2) is better"
    print()
    if sig:
        print(f"VERDICT: statistically significant (p<0.05). Direction: {direction}.")
        print("The Sentinel-1 improvement is unlikely to be due to chance.")
    else:
        print(f"VERDICT: NOT statistically significant (p>=0.05). Direction of "
              f"the (non-significant) mean: {direction}.")
        print("The observed SAR improvement could plausibly be noise on this sample size.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
