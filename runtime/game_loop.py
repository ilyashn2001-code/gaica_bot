from __future__ import annotations

from typing import Any

from actions.models import BotAction
from telemetry.trace import DecisionTrace
from protocol.parser import parse_server_message
from protocol.serializer import serialize_action
from state.world_state import WorldState
from ai.controller import BotController


class GameLoop:
    """
    Главный рантайм-оркестратор.

    Отвечает за pipeline:
    - получить строку от сервера;
    - распарсить сообщение;
    - обновить world state;
    - если это tick -> получить action от AI;
    - провалидировать/подготовить action;
    - сериализовать action;
    - отправить обратно на сервер;
    - сохранить last_valid_command;
    - записать trace.
    """

    def __init__(self, client, logger) -> None:
        self.client = client
        self.logger = logger

        self.world_state = WorldState()
        self.controller = BotController()

        self._is_running = True

    def run(self) -> None:
        """
        Основной цикл обработки сообщений сервера.
        """
        self.client.connect()
        self.logger.info("Connected to game server")

        try:
            while self._is_running:
                raw_line = self.client.read_line()
                self._process_raw_line(raw_line)
        finally:
            self.client.close()
            self.logger.info("Connection closed")

    def _process_raw_line(self, raw_line: str) -> None:
        """
        Обрабатывает одну входящую строку JSON.
        """
        message = parse_server_message(raw_line)
        message_type = message.get("type", "unknown")

        self.logger.debug(f"Received message type={message_type}")

        if message_type == "match_start":
            self._handle_match_start(message)
            return

        if message_type == "round_start":
            self._handle_round_start(message)
            return

        if message_type == "tick":
            self._handle_tick(message)
            return

        if message_type == "round_end":
            self._handle_round_end(message)
            return

        if message_type == "match_end":
            self._handle_match_end(message)
            return

        self.logger.debug(f"Ignoring unsupported message type={message_type}")

    def _handle_match_start(self, message: dict[str, Any]) -> None:
        self.world_state.apply_match_start(message)
        self.logger.info("Handled match_start")

    def _handle_round_start(self, message: dict[str, Any]) -> None:
        self.world_state.apply_round_start(message)
        self.logger.info("Handled round_start")

    def _handle_tick(self, message: dict[str, Any]) -> None:
        self.world_state.apply_tick(message)

        trace = DecisionTrace()

        try:
            action = self.controller.decide(
                world_state=self.world_state,
                trace=trace,
            )

            if action is None:
                self.logger.debug("Controller returned None, using fallback action")
                action = self.world_state.get_safe_fallback_action()

        except Exception as exc:
            self.logger.error(f"Decision error on tick: {exc}")
            action = self.world_state.get_safe_fallback_action()
            trace.add_note(f"decision_exception={exc}")

        self.world_state.last_valid_action = action

        outgoing = serialize_action(action)
        self.client.send_line(outgoing)

        self.logger.debug(f"Sent action: {outgoing}")
        self.logger.debug(f"Decision trace: {trace.to_log_string()}")

    def _handle_round_end(self, message: dict[str, Any]) -> None:
        self.world_state.apply_round_end(message)
        self.logger.info("Handled round_end")

    def _handle_match_end(self, message: dict[str, Any]) -> None:
        self.world_state.apply_match_end(message)
        self.logger.info("Handled match_end")
        self._is_running = False
