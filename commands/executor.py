from collections import deque
from typing import Deque, List, Optional

from commands.command import Command
from infra.trade_logger import TradeLogger


class CommandExecutor:
    def __init__(self, logger: TradeLogger) -> None:
        self._queue: Deque[Command] = deque()
        self._history: List[Command] = []
        self._logger = logger

    @property
    def pending(self) -> int:
        return len(self._queue)

    @property
    def history_size(self) -> int:
        return len(self._history)

    def add_command(self, command: Command) -> None:
        self._queue.append(command)
        self._logger.info(f"queued: {command.description}")

    def execute(self, command: Command) -> None:
        command.execute()
        self._history.append(command)
        self._logger.info(f"executed: {command.description}")

    def execute_all(self) -> int:
        executed = 0
        while self._queue:
            self.execute(self._queue.popleft())
            executed += 1
        return executed

    def undo_last(self) -> Optional[Command]:
        if not self._history:
            return None
        command = self._history.pop()
        command.undo()
        self._logger.info(f"undone: {command.description}")
        return command
