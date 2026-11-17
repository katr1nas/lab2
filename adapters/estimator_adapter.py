import numpy as np

from adapters.third_party import ThirdPartyRLSModel
from estimators.base import HedgeEstimator, Observation


class ThirdPartyEstimatorAdapter(HedgeEstimator):
    def __init__(self, model: ThirdPartyRLSModel) -> None:
        self._model = model

    @property
    def name(self) -> str:
        return "Third-party RLS"

    def fit(self, y: np.ndarray, x: np.ndarray) -> None:
        self._model.calibrate(y.tolist(), x.tolist())

    def update(self, y: float, x: float) -> Observation:
        output = self._model.observe(y, x)
        return Observation(output["residual"], output["sigma"], output["slope"])
