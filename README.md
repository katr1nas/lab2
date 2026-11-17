# Laboratory Work: Behavioral Design Patterns

**Author**: Serghei Barladean FAF-241

---

## Objectives

1. Study and understand the Behavioral Design Patterns.
2. As a continuation of the previous laboratory work, think about what communication between software entities might be involved in the system.
3. Implement some additional functionalities using behavioral design patterns.

---

## Introduction

Behavioral design patterns focus on the interaction and communication between objects: who is responsible for what, and how requests travel through the system. They are valuable when operations have to be scheduled, recorded, reversed or combined.

In my laboratory work I implemented the **Command** behavioral pattern in the Adaptive Hedge Ratio Engine (pairs-trading backtester) built in the previous laboratory works. Before this work, running an experiment and changing a parameter were direct method calls: nothing could be queued, nothing could be reverted and nothing was recorded. The functionalities that I implemented are:

- Encapsulation of experiment operations (run a backtest, change a parameter, clear results) as command objects, enabling queuing, logging and execution at a later time (**Command** pattern);
- Undo of any executed command, including a group of commands treated as one (**Macro command**);
- Decoupling of the code that requests an operation from the code that performs it: the invoker knows only the `Command` interface.

The code is written in Python 3 and uses only NumPy. It extends the code of the previous laboratory works (Builder, Factory Method, Singleton, Adapter, Decorator, Facade), which was reused without changes.

---

## Project Structure

```
Lab3/
├── commands/
│   ├── command.py               # Command interface
│   ├── experiment_commands.py   # RunExperiment, SetParameter, ClearResults, Macro
│   └── executor.py              # CommandExecutor (invoker: queue + history)
├── session/
│   └── experiment_session.py    # ExperimentSession (receiver), RunRecord
├── facade/                      # HedgeLabFacade (Lab2)
├── adapters/                    # Adapter (Lab2)
├── decorators/                  # Decorator (Lab2)
├── backtest/                    # Backtester, Builder, Director, metrics (Lab1)
├── estimators/                  # HedgeEstimator, Static / Kalman / Rolling, factories
├── strategy/                    # SignalStrategy, ZScoreStrategy
├── registry/                    # ResultsRegistry (Singleton)
├── data/ infra/ config.py       # Data sources, logger, configuration
└── main.py                      # Demo of the Command pattern
```

---

## Implementation & Explanation

### Command Pattern

The **Command** pattern turns a request into a stand-alone object that contains everything needed to perform it. It lets the system parametrize operations, put them in a queue, log them and support undo.

The pattern has four participants:

| Participant | Class | Role |
|---|---|---|
| Command | `Command` | Interface with `execute()` and `undo()` |
| Concrete commands | `RunExperimentCommand`, `SetParameterCommand`, `ClearResultsCommand`, `MacroCommand` | One operation each, with the data needed to do and revert it |
| Receiver | `ExperimentSession` | The object that really does the work: runs backtests (through `HedgeLabFacade`), holds the configuration and the stored results |
| Invoker | `CommandExecutor` | Queues, executes and undoes commands without knowing what they do |

#### Command interface
**File**: `commands/command.py`

```python
class Command(ABC):
    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def execute(self) -> None: ...

    @abstractmethod
    def undo(self) -> None: ...
```

#### Concrete commands
**File**: `commands/experiment_commands.py`

Each command stores what it needs to revert itself: the run record, the previous parameter value or the cleared results.

```python
class RunExperimentCommand(Command):
    def __init__(self, session, preset, seed):
        self._session = session
        self._preset = preset
        self._seed = seed
        self._record = None

    def execute(self) -> None:
        self._record = self._session.run(self._preset, self._seed)

    def undo(self) -> None:
        if self._record is not None:
            self._session.remove_run(self._record)
            self._record = None


class SetParameterCommand(Command):
    def execute(self) -> None:
        self._previous = self._session.set_parameter(self._name, self._value)

    def undo(self) -> None:
        if self._previous is not _UNSET:
            self._session.set_parameter(self._name, self._previous)
            self._previous = _UNSET
```

`ClearResultsCommand` keeps a backup of the removed results and restores it on undo.

`MacroCommand` groups several commands into one. It undoes its parts in reverse order, and if one part fails, the already executed parts are rolled back, so a macro is either fully applied or not applied at all:

```python
class MacroCommand(Command):
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
```

#### Receiver
**File**: `session/experiment_session.py`

`ExperimentSession` contains the real logic. `set_parameter` validates the new value (for example `0 <= exit_z < entry_z < stop_z`) before the configuration is changed, so an invalid command never leaves the session in a broken state.

```python
def run(self, preset: str, seed: int) -> RunRecord:
    facade = HedgeLabFacade(self._config, self._logger)
    performance = facade.run_pair(preset, seed)
    record = RunRecord(preset, seed, self._config, performance)
    self._runs.append(record)
    return record
```

#### Invoker
**File**: `commands/executor.py`

```python
class CommandExecutor:
    def add_command(self, command: Command) -> None:
        self._queue.append(command)

    def execute(self, command: Command) -> None:
        command.execute()
        self._history.append(command)

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
        return command
```

A command that raises an error is not added to the history, so `undo_last` never tries to revert something that did not happen.

Client code:

```python
session = ExperimentSession()
executor = CommandExecutor(logger)

executor.add_command(RunExperimentCommand(session, "kalman", 1))
executor.add_command(SetParameterCommand(session, "entry_z", 1.5))
executor.add_command(RunExperimentCommand(session, "kalman", 1))
executor.execute_all()
executor.undo_last()
```

#### Motivation:
The executor does not know how to run a backtest or how to change a configuration; it only works with the `Command` interface. A new operation is a new command class and requires no change in the executor or in the existing commands (Open/Closed Principle). The same objects give queuing, history, undo and grouping for free.

---

## Usage

```bash
pip install -r requirements.txt
python main.py
python main.py queue
python main.py undo
python main.py macro
python main.py errors
```

---

## Screenshots / Results

The outputs below come from a full run of `python main.py`, where the demos follow each other and share one session. Queued commands are executed in order. The same experiment is run with three values of the entry threshold (the INFO lines of the engine are shortened):

```
=== Command queue ===
queued: run kalman on pair 1
queued: set entry_z = 1.5
queued: run kalman on pair 1
queued: set entry_z = 2.5
queued: run kalman on pair 1
pending commands: 5
executed commands: 5

entry_z = 2.5, stored runs = 3
Preset           Pair  entry_z   Sharpe  Trades
kalman              1      2.0     0.07      14
kalman              1      1.5     0.40      31
kalman              1      2.5     0.94       4
```

_Figure 1. Command queue_

Undo of the last three commands restores both the stored results and the parameter:

```
=== Undo ===
undone: run kalman on pair 1
undone: set entry_z = 2.5
undone: run kalman on pair 1

entry_z = 1.5, stored runs = 1
Preset           Pair  entry_z   Sharpe  Trades
kalman              1      2.0     0.07      14
```

_Figure 2. Undo_

A macro command runs three presets on one pair as a single command, and one undo removes all three results:

```
=== Macro command ===
executed: macro 'compare methods on pair 2' (3 commands)

entry_z = 1.5, stored runs = 4
Preset           Pair  entry_z   Sharpe  Trades
kalman              1      2.0     0.07      14
static              2      1.5    -0.12       5
kalman              2      1.5     0.43      35
rolling             2      1.5     0.91      15

undone: macro 'compare methods on pair 2' (3 commands)
entry_z = 1.5, stored runs = 1
```

_Figure 3. Macro command_

Invalid commands are rejected without changing the state. A macro with a failing part is rolled back completely:

```
=== Invalid commands ===
rejected 'set entry_z = 5.0': thresholds must satisfy 0 <= exit_z < entry_z < stop_z
rejected 'set not_a_parameter = 1': Unknown parameter: not_a_parameter. Available: ...
rejected 'run unknown_preset on pair 1': Unknown preset: unknown_preset. Available: ...
history unchanged: True, entry_z = 1.5
macro rolled back: Unknown preset: unknown_preset. Available: ...
entry_z = 1.5, stored runs = 1
after clear: stored runs = 0
after undo of clear: stored runs = 1
```

_Figure 4. Error handling and rollback_

---

## Conclusion

Implementing the **Command** pattern turned the operations of the engine into objects that can be queued, executed later, logged and reverted. The invoker is independent of the concrete operations, the receiver contains the real logic, and the macro command shows that commands can be combined into larger ones with all-or-nothing behavior. Together with the patterns from the previous laboratory works the engine now has creational (Builder, Factory Method, Singleton), structural (Adapter, Decorator, Facade) and behavioral (Command) parts that work together without changes in the existing classes.

Limitation: the Sharpe ratios in the tables come from synthetic data and a single pair, so the difference between the entry thresholds only demonstrates how commands change and record experiments; it is not evidence that a lower or higher threshold is better.
