from typing import Dict, Iterable, Optional, Tuple

from backtest.builder import StandardBacktestBuilder
from backtest.director import BacktestDirector
from backtest.metrics import Performance
from config import BacktestConfig
from data.data_source import SyntheticPairSource
from infra.trade_logger import TradeLogger
from registry.results_registry import ResultsRegistry


class HedgeLabFacade:
    BASELINE = ("static", "kalman", "rolling")
    EXTENDED = BASELINE + ("third_party", "kalman_guarded")

    def __init__(self, config: Optional[BacktestConfig] = None, logger: Optional[TradeLogger] = None) -> None:
        self._config = config or BacktestConfig()
        self._logger = logger or TradeLogger()
        self._builder = StandardBacktestBuilder()
        self._director = BacktestDirector(self._builder, self._config, self._logger)
        self._registry = ResultsRegistry()
        self._presets = {
            "static": self._director.build_static_baseline,
            "kalman": self._director.build_kalman_adaptive,
            "rolling": self._director.build_rolling_benchmark,
            "third_party": self._director.build_third_party_rls,
            "kalman_guarded": self._director.build_kalman_guarded,
            "kalman_logged": self._director.build_kalman_logged,
        }

    @property
    def presets(self) -> Tuple[str, ...]:
        return tuple(self._presets)

    def run_pair(self, preset: str, seed: int) -> Performance:
        if preset not in self._presets:
            raise ValueError(f"Unknown preset: {preset}. Available: {', '.join(self._presets)}")
        self._presets[preset]()
        backtester = self._builder.build()
        source = SyntheticPairSource(seed)
        result = backtester.run(source)
        self._registry.add(source.label, backtester.estimator_name, result)
        return result

    def compare(self, presets: Iterable[str], seeds: Optional[Iterable[int]] = None) -> Dict[str, float]:
        self._registry.clear()
        for seed in seeds or self._config.pair_seeds:
            for preset in presets:
                self.run_pair(preset, seed)
        return self._registry.mean_sharpe()

    def compare_baselines(self) -> Dict[str, float]:
        return self.compare(self.BASELINE)

    def compare_extended(self) -> Dict[str, float]:
        return self.compare(self.EXTENDED)

    def wins(self, method: str, versus: str) -> Tuple[int, int]:
        return self._registry.wins(method, versus)
