"""Representation of the program state."""

from enum import StrEnum


class ProgramState(StrEnum):
    """The state of the program."""

    RUNNING = "running"
    TERMINATED = "terminated"
    PAUSED = "paused"
