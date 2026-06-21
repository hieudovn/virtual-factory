"""OPC UA gateway for publishable industrial telemetry frames.

Exposes each ``SignalValue`` as an OPC UA variable node so external
clients (UaExpert, Ignition, Kepware, …) can browse and subscribe.

The gateway owns an ``asyncua`` server running in a background thread.
Values are written thread-safe via ``run_coroutine_threadsafe``.

.. note::
    This gateway publishes already-built telemetry frames only.  It never
    reads runtime truth state directly.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.telemetry.signal_value import SignalValue

# Default OPC UA TCP endpoint.
_DEFAULT_ENDPOINT = "opc.tcp://0.0.0.0:4840"
_DEFAULT_NAMESPACE = "VirtualFactory"
_SERVER_NAME = "Virtual Factory OPC UA Gateway"


@dataclass(slots=True)
class OpcUaGateway:
    """OPC UA server that exposes publishable ``SignalValue`` frames.

    Parameters
    ----------
    endpoint : str
        OPC UA TCP endpoint (default ``opc.tcp://0.0.0.0:4840``).
    namespace_uri : str
        OPC UA namespace URI (default ``VirtualFactory``).
    enabled : bool
        When ``False`` the gateway is a no-op (useful for testing).
    """

    endpoint: str = _DEFAULT_ENDPOINT
    namespace_uri: str = _DEFAULT_NAMESPACE
    enabled: bool = True

    # Internal — set during connect / first publish
    server: Any | None = field(default=None, repr=False)
    _idx: int = 0  # namespace index, assigned after server creation
    _nodes: dict[str, Any] = field(default_factory=dict)
    _loop: asyncio.AbstractEventLoop | None = field(default=None, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _started: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Start the OPC UA server in a background thread."""
        if not self.enabled or self._started:
            return
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        self._started = True

    def disconnect(self) -> None:
        """Stop the background OPC UA server."""
        if self.server is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self.server.stop(), self._loop)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._started = False
        self._nodes.clear()

    def publish_frame(self, frame: list[SignalValue]) -> None:
        """Write each allowed ``SignalValue`` to its OPC UA variable.

        If this is the first call the OPC UA server is created lazily
        (so tests that never call ``publish_frame`` don't need the
        ``asyncua`` dependency).
        """
        if not self.enabled:
            return
        if not self._started:
            self.connect()
        if self._loop is None or self.server is None:
            return
        for signal in frame:
            if not isinstance(signal, SignalValue):
                raise TypeError("OpcUaGateway.publish_frame accepts SignalValue objects only.")
            if signal.category == "internal_truth":
                raise ValueError(f"Refusing to publish internal_truth signal: {signal.name}")

            node = self._nodes.get(signal.name)
            if node is None:
                node = self._create_variable(signal)
                self._nodes[signal.name] = node
            self._write_value(node, signal)

    # ------------------------------------------------------------------
    # Server lifecycle (runs in background thread)
    # ------------------------------------------------------------------

    def _run_server(self) -> None:
        assert self._loop is not None
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self) -> None:
        try:
            from asyncua import Server
            from asyncua.server.users import UserRole
        except ImportError as exc:
            raise RuntimeError(
                "OPC UA support requires installing the opcua extra: "
                "pip install -e .[opcua]"
            ) from exc

        self.server = Server()
        await self.server.init()
        self.server.set_endpoint(self.endpoint)
        self.server.set_server_name(_SERVER_NAME)

        self._idx = await self.server.register_namespace(self.namespace_uri)

        # Set anonymous access
        self.server.user_manager.set_user_policy(
            [], UserRole.Anonymous, can_read=True, can_write=True
        )

        async with self.server:
            # Keep running until stop() is called
            while True:
                await asyncio.sleep(1.0)

    # ------------------------------------------------------------------
    # Node management (called from simulation thread)
    # ------------------------------------------------------------------

    def _create_variable(self, signal: SignalValue) -> Any:
        """Create an OPC UA variable node for *signal* (blocking)."""
        assert self._loop is not None
        future = asyncio.run_coroutine_threadsafe(
            self._create_variable_async(signal), self._loop
        )
        return future.result(timeout=10.0)

    async def _create_variable_async(self, signal: SignalValue):
        from asyncua import ua

        folder = await self._ensure_folder(signal.category)

        browse_name = f"{self._idx}:{signal.name}"
        node = await self.server.nodes.objects.add_variable(
            parent=folder,
            nodeid=self._next_node_id(signal.name),
            browsename=browse_name,
            datatype=self._ua_type(signal.value),
        )
        await node.set_writable(True)

        # Add engineering units property when available
        if signal.unit:
            try:
                await node.write_attribute(
                    ua.AttributeIds.EURange,
                    ua.DataValue(ua.Range()),
                )
            except Exception:
                pass  # EURange may not be supported in all asyncua versions

        return node

    async def _ensure_folder(self, category: str):
        """Return (or create) a folder for the given signal category."""
        from asyncua import ua

        folder_name = category.replace("_", " ").title()
        browse_name = f"{self._idx}:{folder_name}"

        # Look for existing folder
        objects = self.server.nodes.objects
        children = await objects.get_children()
        for child in children:
            try:
                display = await child.read_display_name()
                if display.Text == folder_name:
                    return child
            except Exception:
                continue

        # Create new folder
        folder = await objects.add_folder(
            self._next_node_id(f"folder_{category}"),
            browse_name,
        )
        return folder

    def _write_value(self, node, signal: SignalValue) -> None:
        """Thread-safe write to an OPC UA variable node."""
        assert self._loop is not None
        from asyncua import ua

        dv = ua.DataValue(ua.Variant(signal.value, self._ua_type(signal.value)))
        asyncio.run_coroutine_threadsafe(
            node.write_attribute(ua.AttributeIds.Value, dv),
            self._loop,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _next_node_id(self, suffix: str) -> str:
        """Generate a node id under our namespace."""
        return f"ns={self._idx};s={suffix}"

    @staticmethod
    def _ua_type(value: object) -> Any:
        """Map Python type to OPC UA type."""
        from asyncua import ua

        if isinstance(value, bool):
            return ua.VariantType.Boolean
        if isinstance(value, int):
            return ua.VariantType.Int64
        if isinstance(value, float):
            return ua.VariantType.Double
        return ua.VariantType.String
