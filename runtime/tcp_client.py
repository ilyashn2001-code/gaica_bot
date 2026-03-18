import socket
from typing import Optional


class TcpGameClient:
    """
    Низкоуровневый TCP-клиент для взаимодействия с игровым сервером.

    Отвечает только за:
    - подключение;
    - чтение строк;
    - отправку строк;
    - закрытие соединения.

    Не должен содержать игровой логики.
    """

    def __init__(self, host: str, port: int, timeout_seconds: float = 1.0) -> None:
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds

        self._socket: Optional[socket.socket] = None
        self._reader = None
        self._writer = None

    def connect(self) -> None:
        """
        Устанавливает TCP-соединение и подготавливает потоковое чтение/запись.
        """
        if self._socket is not None:
            return

        sock = socket.create_connection((self.host, self.port), timeout=self.timeout_seconds)
        sock.settimeout(self.timeout_seconds)

        # makefile удобно использовать для построчного чтения/записи
        self._socket = sock
        self._reader = sock.makefile("r", encoding="utf-8", newline="\n")
        self._writer = sock.makefile("w", encoding="utf-8", newline="\n")

    def read_line(self) -> str:
        """
        Читает одну строку от сервера.

        Возвращает строку без завершающего '\\n'.

        Исключения:
        - RuntimeError, если соединение не установлено;
        - ConnectionError, если соединение закрыто.
        """
        if self._reader is None:
            raise RuntimeError("TCP client is not connected")

        line = self._reader.readline()
        if line == "":
            raise ConnectionError("Connection closed by remote host")

        return line.rstrip("\n")

    def send_line(self, line: str) -> None:
        """
        Отправляет одну строку серверу.

        Сам добавляет завершающий перевод строки.
        """
        if self._writer is None:
            raise RuntimeError("TCP client is not connected")

        self._writer.write(line + "\n")
        self._writer.flush()

    def close(self) -> None:
        """
        Аккуратно закрывает writer, reader и socket.
        """
        try:
            if self._writer is not None:
                self._writer.close()
        finally:
            self._writer = None

        try:
            if self._reader is not None:
                self._reader.close()
        finally:
            self._reader = None

        try:
            if self._socket is not None:
                self._socket.close()
        finally:
            self._socket = None

    def __enter__(self) -> "TcpGameClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
