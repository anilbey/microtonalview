"""Representation of the program state."""

from enum import StrEnum


class ProgramState(StrEnum):
    """The state of the program."""

    PLAYING = "playing"
    TERMINATED = "terminated"
    PAUSED = "paused"
    MENU = "menu"
