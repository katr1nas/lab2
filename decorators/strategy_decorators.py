from strategy.signal_strategy import SignalStrategy


class StrategyDecorator(SignalStrategy):
    def __init__(self, inner: SignalStrategy) -> None:
        self._inner = inner

    def next_position(self, z: float, current: int) -> int:
        return self._inner.next_position(z, current)


class CooldownStrategy(StrategyDecorator):
    def __init__(self, inner: SignalStrategy, steps: int) -> None:
        super().__init__(inner)
        self._steps = steps
        self._remaining = 0

    def next_position(self, z: float, current: int) -> int:
        proposed = super().next_position(z, current)
        if current != 0 and proposed == 0:
            self._remaining = self._steps
            return 0
        if current == 0 and self._remaining > 0:
            self._remaining -= 1
            return 0
        return proposed
