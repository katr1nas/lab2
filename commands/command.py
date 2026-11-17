from abc import ABC, abstractmethod


class Command(ABC):
    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def execute(self) -> None:
        ...

    @abstractmethod
    def undo(self) -> None:
        ...
