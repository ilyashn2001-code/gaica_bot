from enum import StrEnum


class ServerMessageType(StrEnum):
    MATCH_START = "match_start"
    ROUND_START = "round_start"
    TICK = "tick"
    ROUND_END = "round_end"
    MATCH_END = "match_end"


class ClientCommandType(StrEnum):
    COMMAND = "command"
