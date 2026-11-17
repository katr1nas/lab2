import dataclasses
from dataclasses import dataclass
from typing import Any, List, Optional

from backtest.metrics import Performance
from config import BacktestConfig
from facade.hedge_lab import HedgeLabFacade
from infra.trade_logger import TradeLogger


@dataclass(frozen=True)
class RunRecord:
    preset: str
    seed: int
    config: BacktestConfig
    performance: Performance


class ExperimentSession:
    _LOCKED = ("pair_seeds",)

    def __init__(self, config: Optional[BacktestConfig] = None, logger: Optional[TradeLogger] = None) -> None:
        self._config = config or BacktestConfig()
        self._logger = logger or TradeLogger("session")
        self._runs: List[RunRecord] = []

    @property
    def config(self) -> BacktestConfig:
        return self._config

    @property
    def runs(self) -> List[RunRecord]:
        return list(self._runs)

    def set_parameter(self, name: str, value: Any) -> Any:
        names = sorted({f.name for f in dataclasses.fields(self._config)} - set(self._LOCKED))
        if name not in names:
            raise ValueError(f"Unknown parameter: {name}. Available: {', '.join(names)}")
        previous = getattr(self._config, name)
        if isinstance(previous, int) and value != int(value):
            raise ValueError(f"{name} must be an integer, got {value}")
        candidate = dataclasses.replace(self._config, **{name: type(previous)(value)})
        self._validate(candidate)
        self._config = candidate
        return previous

    @staticmethod
    def _validate(config: BacktestConfig) -> None:
        if not 0.0 < config.train_ratio < 1.0:
            raise ValueError("train_ratio must be between 0 and 1")
        if not 0.0 <= config.exit_z < config.entry_z < config.stop_z:
            raise ValueError("thresholds must satisfy 0 <= exit_z < entry_z < stop_z")
        if config.transaction_cost < 0:
            raise ValueError("transaction_cost must not be negative")
        if config.rolling_window < 10:
            raise ValueError("rolling_window must be at least 10")
        if config.warmup_steps < 0 or config.cooldown_steps < 0:
            raise ValueError("warmup_steps and cooldown_steps must not be negative")

    def run(self, preset: str, seed: int) -> RunRecord:
        facade = HedgeLabFacade(self._config, self._logger)
        performance = facade.run_pair(preset, seed)
        record = RunRecord(preset, seed, self._config, performance)
        self._runs.append(record)
        return record

    def remove_run(self, record: RunRecord) -> None:
        self._runs.remove(record)

    def clear_runs(self) -> List[RunRecord]:
        removed = self._runs
        self._runs = []
        return removed

    def restore_runs(self, runs: List[RunRecord]) -> None:
        self._runs = list(runs)
