from typing import Any, List, Optional

from commands.command import Command
from session.experiment_session import ExperimentSession, RunRecord

_UNSET = object()


class RunExperimentCommand(Command):
    def __init__(self, session: ExperimentSession, preset: str, seed: int) -> None:
        self._session = session
        self._preset = preset
        self._seed = seed
        self._record: Optional[RunRecord] = None

    @property
    def description(self) -> str:
        return f"run {self._preset} on pair {self._seed}"

    @property
    def record(self) -> Optional[RunRecord]:
        return self._record

    def execute(self) -> None:
        self._record = self._session.run(self._preset, self._seed)

    def undo(self) -> None:
        if self._record is not None:
            self._session.remove_run(self._record)
            self._record = None


class SetParameterCommand(Command):
    def __init__(self, session: ExperimentSession, name: str, value: Any) -> None:
        self._session = session
        self._name = name
        self._value = value
        self._previous: Any = _UNSET

    @property
    def description(self) -> str:
        return f"set {self._name} = {self._value}"

    def execute(self) -> None:
        self._previous = self._session.set_parameter(self._name, self._value)

    def undo(self) -> None:
        if self._previous is not _UNSET:
            self._session.set_parameter(self._name, self._previous)
            self._previous = _UNSET


class ClearResultsCommand(Command):
    def __init__(self, session: ExperimentSession) -> None:
        self._session = session
        self._backup: Optional[List[RunRecord]] = None

    @property
    def description(self) -> str:
        return "clear results"

    def execute(self) -> None:
        self._backup = self._session.clear_runs()

    def undo(self) -> None:
        if self._backup is not None:
            self._session.restore_runs(self._backup)
            self._backup = None


class MacroCommand(Command):
    def __init__(self, label: str, commands: List[Command]) -> None:
        self._label = label
        self._commands = list(commands)
        self._done: List[Command] = []

    @property
    def description(self) -> str:
        return f"macro '{self._label}' ({len(self._commands)} commands)"

    def execute(self) -> None:
        self._done = []
        try:
            for command in self._commands:
                command.execute()
                self._done.append(command)
        except Exception:
            self.undo()
            raise

    def undo(self) -> None:
        for command in reversed(self._done):
            command.undo()
        self._done = []
