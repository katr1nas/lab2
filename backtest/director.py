from backtest.builder import BacktestBuilder
from config import BacktestConfig
from decorators.estimator_decorators import LoggingEstimator, WarmupEstimator
from decorators.strategy_decorators import CooldownStrategy
from estimators.factory import get_factory
from infra.trade_logger import TradeLogger
from strategy.signal_strategy import SignalStrategy, ZScoreStrategy


class BacktestDirector:
    def __init__(self, builder: BacktestBuilder, config: BacktestConfig, logger: TradeLogger) -> None:
        self._builder = builder
        self._config = config
        self._logger = logger

    def _zscore(self) -> SignalStrategy:
        return ZScoreStrategy(self._config.entry_z, self._config.exit_z, self._config.stop_z)

    def _configure_common(self) -> None:
        self._builder.set_config(self._config)
        self._builder.set_logger(self._logger)
        self._builder.set_strategy(self._zscore())

    def build_static_baseline(self) -> None:
        self._configure_common()
        self._builder.set_estimator(get_factory("static").create(self._config))

    def build_kalman_adaptive(self) -> None:
        self._configure_common()
        self._builder.set_estimator(get_factory("kalman").create(self._config))

    def build_rolling_benchmark(self) -> None:
        self._configure_common()
        self._builder.set_estimator(get_factory("rolling").create(self._config))

    def build_third_party_rls(self) -> None:
        self._configure_common()
        self._builder.set_estimator(get_factory("third_party").create(self._config))

    def build_kalman_guarded(self) -> None:
        self._configure_common()
        kalman = get_factory("kalman").create(self._config)
        self._builder.set_estimator(WarmupEstimator(kalman, self._config.warmup_steps))
        self._builder.set_strategy(CooldownStrategy(self._zscore(), self._config.cooldown_steps))

    def build_kalman_logged(self) -> None:
        self._configure_common()
        kalman = get_factory("kalman").create(self._config)
        self._builder.set_estimator(LoggingEstimator(kalman, self._logger, self._config.log_every))
