from typing import Dict, List

import numpy as np

from data.data_source import SyntheticPairSource


class ThirdPartyRLSModel:
    def __init__(self, forgetting: float = 0.998, variance_decay: float = 0.99) -> None:
        self.forgetting = forgetting
        self.variance_decay = variance_decay
        self.intercept = 0.0
        self.slope = 1.0
        self.residual_variance = 1.0
        self._cov = np.eye(2) * 1e-2

    def calibrate(self, series_a: List[float], series_b: List[float]) -> None:
        a = np.asarray(series_a, dtype=float)
        b = np.asarray(series_b, dtype=float)
        design = np.column_stack([np.ones_like(b), b])
        coef, *_ = np.linalg.lstsq(design, a, rcond=None)
        self.intercept, self.slope = float(coef[0]), float(coef[1])
        self.residual_variance = float(np.var(a - design @ coef, ddof=1))
        self._cov = np.eye(2) * 1e-2
        for price_a, price_b in zip(a, b):
            self.observe(float(price_a), float(price_b))

    def observe(self, price_a: float, price_b: float) -> Dict[str, float]:
        h = np.array([1.0, price_b])
        theta = np.array([self.intercept, self.slope])
        error = price_a - h @ theta
        sigma = float(np.sqrt(self.residual_variance))
        ph = self._cov @ h
        gain = ph / (self.forgetting + h @ ph)
        theta = theta + gain * error
        self._cov = (self._cov - np.outer(gain, ph)) / self.forgetting
        self.intercept, self.slope = float(theta[0]), float(theta[1])
        self.residual_variance = (
            self.variance_decay * self.residual_variance + (1.0 - self.variance_decay) * error ** 2
        )
        return {
            "residual": float(error),
            "sigma": sigma,
            "slope": self.slope,
            "intercept": self.intercept,
        }


class ThirdPartyPriceFeed:
    def __init__(self, seed: int, ticker_a: str = "ALFA", ticker_b: str = "BETA") -> None:
        self._seed = seed
        self.ticker_a = ticker_a
        self.ticker_b = ticker_b

    def describe(self) -> str:
        return f"{self.ticker_a}/{self.ticker_b}#{self._seed}"

    def fetch_quotes(self) -> List[Dict[str, float]]:
        log_a, log_b = SyntheticPairSource(self._seed).load()
        return [
            {"close_a": float(np.exp(a)), "close_b": float(np.exp(b))}
            for a, b in zip(log_a, log_b)
        ]
