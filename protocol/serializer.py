import json
from typing import Any

from actions.models import BotAction
from protocol.messages import ClientCommandType


def serialize_action(action: BotAction) -> str:
    """
    Преобразует внутреннюю команду BotAction в JSON-строку
    для отправки на игровой сервер.
    """
    payload = action_to_payload(action)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def action_to_payload(action: BotAction) -> dict[str, Any]:
    """
    Преобразует BotAction в словарь, готовый к JSON-сериализации.
    """
    return {
        "type": ClientCommandType.COMMAND,
        "payload": {
            "move": {
                "x": action.move_x,
                "y": action.move_y,
            },
            "aim": {
                "x": action.aim_x,
                "y": action.aim_y,
            },
            "shoot": action.shoot,
            "kick": action.kick,
            "pickup": action.pickup,
            "drop": action.drop,
            "throw": action.throw,
            "interact": action.interact,
        },
    }
