import numpy as np

from estimators.base import HedgeEstimator, Observation
from infra.trade_logger import TradeLogger


class EstimatorDecorator(HedgeEstimator):
    def __init__(self, inner: HedgeEstimator) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    def fit(self, y: np.ndarray, x: np.ndarray) -> None:
        self._inner.fit(y, x)

    def update(self, y: float, x: float) -> Observation:
        return self._inner.update(y, x)


class LoggingEstimator(EstimatorDecorator):
    def __init__(self, inner: HedgeEstimator, logger: TradeLogger, every: int = 100) -> None:
        super().__init__(inner)
        self._logger = logger
        self._every = every
        self._count = 0

    def fit(self, y: np.ndarray, x: np.ndarray) -> None:
        self._logger.info(f"{self._inner.name}: fit on {len(y)} observations")
        super().fit(y, x)
        self._count = 0

    def update(self, y: float, x: float) -> Observation:
        observation = super().update(y, x)
        self._count += 1
        if self._count % self._every == 0:
            self._logger.info(
                f"{self._inner.name}: step {self._count} "
                f"beta={observation.beta:.4f} spread={observation.spread:+.4f}"
            )
        return observation


class WarmupEstimator(EstimatorDecorator):
    def __init__(self, inner: HedgeEstimator, warmup: int) -> None:
        super().__init__(inner)
        self._warmup = warmup
        self._seen = 0

    @property
    def name(self) -> str:
        return f"{self._inner.name}+Warmup({self._warmup})"

    def fit(self, y: np.ndarray, x: np.ndarray) -> None:
        super().fit(y, x)
        self._seen = 0

    def update(self, y: float, x: float) -> Observation:
        observation = super().update(y, x)
        self._seen += 1
        if self._seen <= self._warmup:
            return Observation(0.0, observation.scale, observation.beta)
        return observation
