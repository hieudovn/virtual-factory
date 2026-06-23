"""Asset Hierarchy System.

Models parent-child relationships for complex equipment assemblies
like Compressor Trains, Pump Systems, etc.

An asset hierarchy is a tree where:
- Leaf nodes are equipment models (compressor, motor, valve, etc.)
- Internal nodes are assemblies (compressor train, lube oil system, etc.)
- The root is the top-level asset

The hierarchy drives:
- Tag naming (COMP_TRAIN_01.MOTOR.current)
- Fault propagation (bearing wear in motor affects compressor train health)
- Benchmark label aggregation
- UI asset tree display
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AssetNode:
    """A node in the asset hierarchy tree.

    Attributes
    ----------
    asset_id : str
        Unique identifier (e.g. ``COMP_TRAIN_01``).
    asset_type : str
        Type category (e.g. ``compressor_train``, ``pump_system``).
    display_name : str
        Human-readable name.
    parent : AssetNode | None
        Parent node in the hierarchy.
    children : dict[str, AssetNode]
        Child assets keyed by asset_id.
    equipment_ref : str | None
        Reference to the equipment config ID, if this is a leaf.
    tags : list[str]
        Tag names associated with this asset.
    metadata : dict
        Arbitrary asset metadata.
    """
    asset_id: str
    asset_type: str
    display_name: str = ""
    parent: "AssetNode | None" = None
    children: dict[str, "AssetNode"] = field(default_factory=dict)
    equipment_ref: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def path(self) -> str:
        """Full hierarchical path from root (e.g. ``COMP_TRAIN_01.MOTOR.BEARING_DE``)."""
        if self.parent is None:
            return self.asset_id
        return f"{self.parent.path}.{self.asset_id}"

    def add_child(self, node: "AssetNode") -> None:
        """Add a child asset node."""
        node.parent = self
        self.children[node.asset_id] = node

    def get_descendant_tags(self) -> list[str]:
        """Get all tags from this node and its descendants."""
        result = list(self.tags)
        for child in self.children.values():
            result.extend(child.get_descendant_tags())
        return result

    def find(self, asset_id: str) -> "AssetNode | None":
        """Find a node by asset_id in the subtree."""
        if self.asset_id == asset_id:
            return self
        for child in self.children.values():
            found = child.find(asset_id)
            if found is not None:
                return found
        return None

    def flatten(self) -> list["AssetNode"]:
        """Return flat list of all nodes in pre-order."""
        result = [self]
        for child in self.children.values():
            result.extend(child.flatten())
        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for export."""
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "display_name": self.display_name,
            "path": self.path,
            "parent_id": self.parent.asset_id if self.parent else None,
            "equipment_ref": self.equipment_ref,
            "is_leaf": self.is_leaf,
            "tag_count": len(self.get_descendant_tags()),
            "metadata": self.metadata,
        }


@dataclass
class AssetHierarchy:
    """Manages the full asset tree for a plant configuration.

    Usage::

        hierarchy = AssetHierarchy()
        train = hierarchy.add_root("COMP_TRAIN_01", "compressor_train",
                                    "Compressor Train A")
        motor = AssetNode("MOTOR", "driver_motor", "Main Drive Motor",
                          equipment_ref="MTR01")
        train.add_child(motor)
        hierarchy.add_node(motor)

        # Query
        all_tags = train.get_descendant_tags()
        flat = hierarchy.flatten()
    """

    roots: dict[str, AssetNode] = field(default_factory=dict)
    _node_index: dict[str, AssetNode] = field(default_factory=dict)

    def add_root(self, asset_id: str, asset_type: str, display_name: str = "") -> AssetNode:
        """Create and register a root asset."""
        node = AssetNode(asset_id=asset_id, asset_type=asset_type, display_name=display_name)
        self.roots[asset_id] = node
        self._node_index[asset_id] = node
        return node

    def add_node(self, node: AssetNode) -> None:
        """Register an existing node in the index."""
        self._node_index[node.asset_id] = node

    def find(self, asset_id: str) -> AssetNode | None:
        """Find any node by asset_id."""
        return self._node_index.get(asset_id)

    def flatten(self) -> list[AssetNode]:
        """Return all nodes in the hierarchy."""
        result: list[AssetNode] = []
        for root in self.roots.values():
            result.extend(root.flatten())
        return result

    def get_all_tags(self) -> list[str]:
        """Get all tags across the entire hierarchy."""
        result: list[str] = []
        for root in self.roots.values():
            result.extend(root.get_descendant_tags())
        return result

    def export_metadata(self) -> list[dict[str, Any]]:
        """Export asset metadata for analytics."""
        return [node.to_dict() for node in self.flatten()]

    def get_tag_count(self) -> int:
        """Total number of unique tags across the hierarchy."""
        return len(set(self.get_all_tags()))
