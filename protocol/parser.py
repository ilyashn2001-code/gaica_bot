import json
from typing import Any

from protocol.messages import ServerMessageType


def parse_server_message(raw_line: str) -> dict[str, Any]:
    """
    Преобразует одну входящую JSON-строку от сервера в словарь.

    Гарантии:
    - возвращает dict;
    - проверяет наличие поля "type";
    - нормализует message["type"] к строке.

    Исключения:
    - ValueError, если JSON невалиден;
    - TypeError, если корень JSON не объект;
    - KeyError, если нет поля "type".
    """
    try:
        data = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON from server: {exc}") from exc

    if not isinstance(data, dict):
        raise TypeError("Server message root must be a JSON object")

    if "type" not in data:
        raise KeyError("Server message does not contain required field 'type'")

    message_type = data["type"]
    if not isinstance(message_type, str):
        raise TypeError("Server message field 'type' must be a string")

    data["type"] = message_type.strip()

    return data


def is_match_start(message: dict[str, Any]) -> bool:
    return message.get("type") == ServerMessageType.MATCH_START


def is_round_start(message: dict[str, Any]) -> bool:
    return message.get("type") == ServerMessageType.ROUND_START


def is_tick(message: dict[str, Any]) -> bool:
    return message.get("type") == ServerMessageType.TICK


def is_round_end(message: dict[str, Any]) -> bool:
    return message.get("type") == ServerMessageType.ROUND_END


def is_match_end(message: dict[str, Any]) -> bool:
    return message.get("type") == ServerMessageType.MATCH_END
