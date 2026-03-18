import sys
import traceback

from runtime.tcp_client import TcpGameClient
from runtime.game_loop import GameLoop
from telemetry.logger import get_logger


def parse_args(argv: list[str]) -> tuple[str, int]:
    """
    Ожидаемый формат запуска:
        python3 main.py <host> <port>
    """
    if len(argv) != 3:
        raise ValueError(
            "Usage: python3 main.py <host> <port>"
        )

    host = argv[1]

    try:
        port = int(argv[2])
    except ValueError as exc:
        raise ValueError("Port must be an integer") from exc

    if not (1 <= port <= 65535):
        raise ValueError("Port must be in range 1..65535")

    return host, port


def main() -> int:
    logger = get_logger("main")

    try:
        host, port = parse_args(sys.argv)
        logger.info(f"Starting bot. host={host}, port={port}")

        client = TcpGameClient(host=host, port=port)
        loop = GameLoop(client=client, logger=logger)

        loop.run()

        logger.info("Bot finished successfully")
        return 0

    except KeyboardInterrupt:
        logger.error("Bot interrupted by user")
        return 130

    except Exception as exc:
        logger.error(f"Fatal error: {exc}")
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
