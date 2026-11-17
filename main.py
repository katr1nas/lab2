import argparse

from commands.executor import CommandExecutor
from commands.experiment_commands import (
    ClearResultsCommand,
    MacroCommand,
    RunExperimentCommand,
    SetParameterCommand,
)
from infra.trade_logger import TradeLogger
from session.experiment_session import ExperimentSession


def title(text: str) -> None:
    print(f"\n=== {text} ===")


def show_state(session: ExperimentSession) -> None:
    print(f"\nentry_z = {session.config.entry_z}, stored runs = {len(session.runs)}")
    if session.runs:
        print(f"{'Preset':<16}{'Pair':>5}{'entry_z':>9}{'Sharpe':>9}{'Trades':>8}")
        for run in session.runs:
            print(
                f"{run.preset:<16}{run.seed:>5}{run.config.entry_z:>9.1f}"
                f"{run.performance.sharpe:>9.2f}{run.performance.trades:>8}"
            )


def demo_queue(session: ExperimentSession, executor: CommandExecutor) -> None:
    title("Command queue")
    executor.add_command(RunExperimentCommand(session, "kalman", 1))
    executor.add_command(SetParameterCommand(session, "entry_z", 1.5))
    executor.add_command(RunExperimentCommand(session, "kalman", 1))
    executor.add_command(SetParameterCommand(session, "entry_z", 2.5))
    executor.add_command(RunExperimentCommand(session, "kalman", 1))
    print(f"pending commands: {executor.pending}")
    executed = executor.execute_all()
    print(f"executed commands: {executed}")
    show_state(session)


def demo_undo(session: ExperimentSession, executor: CommandExecutor) -> None:
    title("Undo")
    for _ in range(3):
        executor.undo_last()
    show_state(session)


def demo_macro(session: ExperimentSession, executor: CommandExecutor) -> None:
    title("Macro command")
    sweep = MacroCommand(
        "compare methods on pair 2",
        [RunExperimentCommand(session, preset, 2) for preset in ("static", "kalman", "rolling")],
    )
    executor.execute(sweep)
    show_state(session)
    executor.undo_last()
    print("\nafter undo of the macro:")
    show_state(session)


def demo_errors(session: ExperimentSession, executor: CommandExecutor) -> None:
    title("Invalid commands")
    history_before = executor.history_size
    for command in (
        SetParameterCommand(session, "entry_z", 5.0),
        SetParameterCommand(session, "not_a_parameter", 1),
        RunExperimentCommand(session, "unknown_preset", 1),
    ):
        try:
            executor.execute(command)
        except ValueError as error:
            print(f"rejected '{command.description}': {error}")
    print(f"history unchanged: {executor.history_size == history_before}, entry_z = {session.config.entry_z}")

    broken = MacroCommand(
        "broken macro",
        [
            SetParameterCommand(session, "entry_z", 1.8),
            RunExperimentCommand(session, "kalman", 3),
            RunExperimentCommand(session, "unknown_preset", 3),
        ],
    )
    try:
        executor.execute(broken)
    except ValueError as error:
        print(f"macro rolled back: {error}")
    print(f"entry_z = {session.config.entry_z}, stored runs = {len(session.runs)}")

    executor.execute(ClearResultsCommand(session))
    print(f"after clear: stored runs = {len(session.runs)}")
    executor.undo_last()
    print(f"after undo of clear: stored runs = {len(session.runs)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("demo", nargs="?", default="all", choices=["queue", "undo", "macro", "errors", "all"])
    demo = parser.parse_args().demo

    logger = TradeLogger("lab3")
    session = ExperimentSession(logger=logger)
    executor = CommandExecutor(logger)

    steps = {
        "queue": demo_queue,
        "undo": demo_undo,
        "macro": demo_macro,
        "errors": demo_errors,
    }
    if demo == "all":
        for step in steps.values():
            step(session, executor)
    else:
        if demo in ("undo", "macro", "errors"):
            demo_queue(session, executor)
        steps[demo](session, executor)


if __name__ == "__main__":
    main()
