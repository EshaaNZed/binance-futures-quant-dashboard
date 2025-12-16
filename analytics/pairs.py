from typing import Tuple

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
from statsmodels.tsa.stattools import adfuller  # ADF test. [web:44][web:49]


def compute_hedge_ratio(px_x: pd.Series, px_y: pd.Series) -> float:
    """OLS regression of X on Y: X = a + b*Y; return b."""
    aligned = pd.concat([px_x, px_y], axis=1, join="inner").dropna()
    if len(aligned) < 10:
        return np.nan
    y = aligned.iloc[:, 0].values
    x = aligned.iloc[:, 1].values
    X = add_constant(x)
    model = OLS(y, X).fit()
    return float(model.params[1])


def compute_spread_and_zscore(
    px_x: pd.Series,
    px_y: pd.Series,
    window: int = 100,
) -> Tuple[pd.Series, pd.Series]:
    """Compute spread = X - beta*Y and its rolling z-score."""
    beta = compute_hedge_ratio(px_x, px_y)
    if np.isnan(beta):
        return pd.Series(dtype=float), pd.Series(dtype=float)

    spread = px_x - beta * px_y
    roll_mean = spread.rolling(window=window, min_periods=window // 2).mean()
    roll_std = spread.rolling(window=window, min_periods=window // 2).std()
    z = (spread - roll_mean) / roll_std
    return spread, z


def compute_rolling_corr(
    px_x: pd.Series,
    px_y: pd.Series,
    window: int = 100,
) -> pd.Series:
    aligned = pd.concat([px_x, px_y], axis=1, join="inner").dropna()
    if len(aligned) < window:
        return pd.Series(dtype=float)
    return (
        aligned.iloc[:, 0]
        .rolling(window=window)
        .corr(aligned.iloc[:, 1])
    )


def run_adf_test(spread: pd.Series):
    """Return ADF statistic and p-value."""
    spread = spread.dropna()
    if len(spread) < 20:
        return None, None
    result = adfuller(spread.values)  # standard usage. [web:44][web:47]
    stat, pvalue = result[0], result[1]
    return float(stat), float(pvalue)
