"""Async protocol client for NAD Txx7 AVR RS-232/Telnet control."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .const import (
    CONNECTION_RS232,
    CONNECTION_TELNET,
    DEFAULT_BAUDRATE,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class NadConnectionError(Exception):
    """Raised when the NAD connection fails."""


class NadProtocolError(Exception):
    """Raised when NAD protocol data cannot be handled."""


class NadClient:
    """NAD ASCII protocol client.

    The Ethernet and RS-232 transports use the same command grammar:
    ``Prefix.Variable?`` to query and ``Prefix.Variable=value`` to set.
    """

    def __init__(
        self,
        connection_type: str,
        host: str | None = None,
        port: int = DEFAULT_PORT,
        serial_port: str | None = None,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.connection_type = connection_type
        self.host = host
        self.port = port
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.timeout = timeout

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._listen_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._state: dict[str, str] = {}
        self._callbacks: list[Callable[[dict[str, str]], None]] = []
        self._pending: dict[str, list[asyncio.Future[str]]] = defaultdict(list)

    @property
    def is_connected(self) -> bool:
        """Return true when a transport is open."""
        return self._writer is not None and not self._writer.is_closing()

    @property
    def is_listening(self) -> bool:
        """Return true when the background listener is active."""
        return self._listen_task is not None and not self._listen_task.done()

    @property
    def state(self) -> dict[str, str]:
        """Return a snapshot of known variable values."""
        return dict(self._state)

    def register_callback(self, callback: Callable[[dict[str, str]], None]) -> None:
        """Register a state-change callback."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[dict[str, str]], None]) -> None:
        """Unregister a state-change callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def connect(self) -> None:
        """Open the configured transport and start the listener."""
        if self.is_connected:
            return

        try:
            if self.connection_type == CONNECTION_TELNET:
                if not self.host:
                    raise NadConnectionError("Missing host")
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.timeout,
                )
            elif self.connection_type == CONNECTION_RS232:
                if not self.serial_port:
                    raise NadConnectionError("Missing serial port")
                try:
                    import serial_asyncio  # type: ignore[import-not-found]
                except ImportError as exc:
                    raise NadConnectionError(
                        "pyserial-asyncio-fast is required for RS-232 connections"
                    ) from exc
                self._reader, self._writer = await asyncio.wait_for(
                    serial_asyncio.open_serial_connection(
                        url=self.serial_port,
                        baudrate=self.baudrate,
                    ),
                    timeout=self.timeout,
                )
            else:
                raise NadConnectionError(f"Unsupported connection type: {self.connection_type}")
        except asyncio.TimeoutError as exc:
            raise NadConnectionError("Connection timeout") from exc
        except OSError as exc:
            raise NadConnectionError(str(exc)) from exc

        self._listen_task = asyncio.create_task(self._listen())

    async def disconnect(self) -> None:
        """Close the transport and stop the listener."""
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        self._listen_task = None

        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except (OSError, RuntimeError, AttributeError):
                pass
        self._reader = None
        self._writer = None
        self._fail_pending(NadConnectionError("Disconnected"))

    async def query(self, variable: str) -> str | None:
        """Query a variable and return its value."""
        await self._ensure_connected()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        self._pending[variable].append(future)

        await self._send(f"{variable}?")
        try:
            return await asyncio.wait_for(future, timeout=self.timeout)
        except asyncio.TimeoutError:
            self._remove_pending(variable, future)
            _LOGGER.debug("NAD query timed out: %s", variable)
            return None

    async def set_variable(self, variable: str, value: str | int | float) -> bool:
        """Set a variable to a value."""
        await self._ensure_connected()
        await self._send(f"{variable}={value}")
        return True

    async def step_variable(self, variable: str, operator: str) -> bool:
        """Increment or decrement a variable with + or -."""
        if operator not in {"+", "-"}:
            raise NadProtocolError("operator must be + or -")
        await self._ensure_connected()
        await self._send(f"{variable}{operator}")
        return True

    async def send_raw(self, command: str) -> bool:
        """Send a raw NAD command without adding an operator."""
        await self._ensure_connected()
        await self._send(command.strip())
        return True

    async def query_many(self, variables: list[str]) -> dict[str, str]:
        """Query a list of variables, ignoring unsupported timeouts."""
        for variable in variables:
            try:
                await self.query(variable)
            except NadConnectionError:
                raise
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.debug("NAD query failed for %s: %s", variable, exc)
        return self.state

    async def scan_many(
        self,
        variables: list[str],
        command_delay: float = 0.04,
        settle_time: float = 1.0,
    ) -> dict[str, str]:
        """Send many query commands and let the listener collect responses."""
        await self._ensure_connected()
        for variable in variables:
            await self._send(f"{variable}?")
            if command_delay > 0:
                await asyncio.sleep(command_delay)
        await asyncio.sleep(settle_time)
        return self.state

    async def _ensure_connected(self) -> None:
        if not self.is_connected:
            await self.connect()

    async def _send(self, payload: str) -> None:
        if self._writer is None:
            raise NadConnectionError("Not connected")
        data = f"\r{payload}\r".encode("ascii", errors="ignore")
        async with self._lock:
            _LOGGER.debug("NAD TX: %s", payload)
            self._writer.write(data)
            await self._writer.drain()

    async def _listen(self) -> None:
        while self._reader is not None:
            try:
                line = await self._read_line()
                if line:
                    self._handle_line(line)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.warning("NAD listener stopped: %s", exc)
                self._reader = None
                self._writer = None
                self._fail_pending(exc)
                break

    async def _read_line(self) -> str:
        """Read one NAD response terminated by CR, LF, or CRLF."""
        if self._reader is None:
            raise NadConnectionError("Not connected")

        buffer = bytearray()
        while True:
            raw = await self._reader.read(1)
            if not raw:
                raise NadConnectionError("Connection closed")
            if raw in (b"\r", b"\n"):
                if buffer:
                    return buffer.decode("ascii", errors="ignore").strip()
                continue
            buffer.extend(raw)

    def _handle_line(self, line: str) -> None:
        _LOGGER.debug("NAD RX: %s", line)
        if "=" not in line:
            return
        variable, value = line.split("=", 1)
        variable = variable.strip()
        value = value.strip()
        if not variable:
            return

        self._state[variable] = value
        pending = self._pending.pop(variable, [])
        for future in pending:
            if not future.done():
                future.set_result(value)
        self._notify()

    def _notify(self) -> None:
        snapshot = self.state
        for callback in self._callbacks:
            try:
                callback(snapshot)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("NAD state callback failed")

    def _remove_pending(self, variable: str, future: asyncio.Future[str]) -> None:
        if variable not in self._pending:
            return
        try:
            self._pending[variable].remove(future)
        except ValueError:
            return
        if not self._pending[variable]:
            self._pending.pop(variable, None)

    def _fail_pending(self, exc: Exception) -> None:
        for futures in self._pending.values():
            for future in futures:
                if not future.done():
                    future.set_exception(exc)
        self._pending.clear()
