"""OPC UA Gateway for the WTP Simulator.

Exposes all 92 WTP signals as OPC UA variable nodes so external
clients (Edge Agent, UaExpert, Ignition, etc.) can browse and subscribe.

The gateway owns an ``asyncua`` server running in a background thread.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any

_DEFAULT_ENDPOINT = "opc.tcp://0.0.0.0:4840"
_DEFAULT_NAMESPACE = "WTP-Simulator"
_SERVER_NAME = "WTP Simulator OPC UA Gateway"


@dataclass
class WtpOpcUaGateway:
    """OPC UA server that exposes WTP simulator signals.

    Parameters
    ----------
    endpoint : str
        OPC UA TCP endpoint (default ``opc.tcp://0.0.0.0:4841``).
    namespace_uri : str
        OPC UA namespace URI (default ``WTP-Simulator``).
    enabled : bool
        When ``False`` the gateway is a no-op.
    """

    endpoint: str = _DEFAULT_ENDPOINT
    namespace_uri: str = _DEFAULT_NAMESPACE
    enabled: bool = True

    # Internal
    server: Any | None = field(default=None, repr=False)
    _idx: int = 0
    _nodes: dict[str, Any] = field(default_factory=dict)
    _loop: asyncio.AbstractEventLoop | None = field(default=None, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _started: bool = False
    _ready: threading.Event = field(default_factory=threading.Event)
    _stop_requested: threading.Event = field(default_factory=threading.Event)
    _folder_nodes: dict[str, Any] = field(default_factory=dict)

    def connect(self) -> None:
        """Start the OPC UA server in a background thread."""
        if not self.enabled or self._started:
            return
        self._ready.clear()
        self._stop_requested.clear()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10.0):
            raise RuntimeError("WTP OPC UA server failed to initialize within 10 seconds")
        self._started = True

    def disconnect(self) -> None:
        """Stop the background OPC UA server."""
        self._stop_requested.set()
        if self.server is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self.server.stop(), self._loop)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._started = False
        self._nodes.clear()
        self._folder_nodes.clear()
        self._ready.clear()

    def publish_signals(self, signals: dict[str, float | bool]) -> None:
        """Write signal values to OPC UA variable nodes.

        Creates variables lazily on first call for each signal.
        """
        if not self.enabled:
            return
        if not self._started:
            self.connect()
        if self._loop is None or self.server is None or self._idx == 0:
            return

        for name, value in signals.items():
            node = self._nodes.get(name)
            if node is None:
                node = self._create_variable(name, value)
                self._nodes[name] = node
            self._write_value(node, name, value)

    @property
    def node_count(self) -> int:
        """Number of WTP signal value nodes currently exposed."""
        return len(self._nodes)

    def _run_server(self) -> None:
        assert self._loop is not None
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self) -> None:
        try:
            from asyncua import Server
        except ImportError as exc:
            raise RuntimeError(
                "OPC UA support requires asyncua: pip install asyncua"
            ) from exc

        self.server = Server()
        await self.server.init()
        self.server.set_endpoint(self.endpoint)
        self.server.set_server_name(_SERVER_NAME)

        self._idx = await self.server.register_namespace(self.namespace_uri)
        async with self.server:
            self._ready.set()
            while not self._stop_requested.is_set():
                await asyncio.sleep(1.0)

    def _create_variable(self, name: str, value: float | bool) -> Any:
        """Create an OPC UA variable node (blocking)."""
        assert self._loop is not None
        future = asyncio.run_coroutine_threadsafe(
            self._create_variable_async(name, value), self._loop
        )
        return future.result(timeout=10.0)

    async def _create_variable_async(self, name: str, value: float | bool) -> Any:
        from asyncua import ua

        # Categorize by prefix
        folder_name = "99_Other"
        if (
            name.startswith("RAW-WATER-QUALITY")
            or name.startswith("INTAKE-STRUCTURE")
            or name.startswith("RWP-")
            or name.startswith("RAW-WATER-PUMP")
            or name.startswith("RAW-WATER-MANIFOLD")
        ):
            folder_name = "01_Intake"
        elif (
            name.startswith("COAG")
            or name.startswith("CHLORINE")
            or name.startswith("PH-PUMP")
            or "CHEMICAL" in name
            or name.startswith("FLASH-MIXER")
        ):
            folder_name = "02_Chemical_Dosing"
        elif name.startswith("FLOCCULATOR") or name.startswith("CLARIFIER") or name.startswith("SLUDGE-PUMP"):
            folder_name = "03_Clarification"
        elif name.startswith("FILTER") or name.startswith("BACKWASH") or name.startswith("SCREEN"):
            folder_name = "04_Filtration"
        elif name.startswith("CONTACT") or name.startswith("DISINFECTION"):
            folder_name = "05_Disinfection"
        elif name.startswith("CLEAR-WATER") or name.startswith("TRANSFER-PUMP"):
            folder_name = "06_Clear_Water"
        elif (
            name.startswith("HSP-")
            or name.startswith("HIGH-SERVICE")
            or name.startswith("OUTLET-MANIFOLD")
            or name.startswith("TRANSFER-OUTLET")
        ):
            folder_name = "07_Distribution"
        elif name.startswith("PLANT-KPI") or name.startswith("ENERGY") or name.startswith("MCC") or name.startswith("LAB") or name.startswith("QUALITY-TRACEABILITY") or name.startswith("TRANSFORMER"):
            folder_name = "08_KPI_Traceability"

        parent = self._folder_nodes.get(folder_name)
        if parent is None:
            parent = await self._ensure_folder(folder_name)
            self._folder_nodes[folder_name] = parent

        browse_name = f"{self._idx}:{name}"
        variant_type = ua.VariantType.Boolean if isinstance(value, bool) else ua.VariantType.Double
        node_value = bool(value) if isinstance(value, bool) else float(value)

        node = await parent.add_variable(
            nodeid=f"ns={self._idx};s={name}",
            bname=browse_name,
            val=node_value,
            varianttype=variant_type,
        )
        await node.set_writable(True)
        return node

    async def _ensure_folder(self, folder_name: str) -> Any:
        """Return (or create) a folder for the given category."""
        objects = self.server.nodes.objects
        children = await objects.get_children()
        for child in children:
            try:
                display = await child.read_display_name()
                if display.Text == folder_name:
                    return child
            except Exception:
                continue

        folder = await objects.add_folder(
            f"ns={self._idx};s=folder_{folder_name}",
            folder_name,
        )
        return folder

    def _write_value(self, node: Any, name: str, value: float | bool) -> None:
        """Thread-safe write to an OPC UA variable node."""
        assert self._loop is not None
        from asyncua import ua

        variant_type = ua.VariantType.Boolean if isinstance(value, bool) else ua.VariantType.Double
        node_value = bool(value) if isinstance(value, bool) else float(value)
        dv = ua.DataValue(ua.Variant(
            node_value,
            variant_type,
        ))
        asyncio.run_coroutine_threadsafe(
            node.write_attribute(ua.AttributeIds.Value, dv),
            self._loop,
        )
