"""Coordinator ↔ durable material-ledger committed-fact bridge.

The material journal remains the sole durable material authority.  The event
ledger is a rebuildable in-memory projection written only by the existing
serial coordinator.
"""

from virtual_factory.factory.integration.checkpoint import (
    build_bridge_checkpoint,
    validate_bridge_checkpoint,
)
from virtual_factory.factory.integration.contracts import (
    CHECKPOINT_SCHEMA_VERSION,
    BridgeCheckpoint,
    BridgeCheckpointError,
    BridgeContractError,
    BridgeError,
    BridgeIdentity,
    BridgeIdentityError,
    BridgePolicy,
    BridgeProjectionError,
    BridgeRecoveryRequired,
    BridgeStateError,
    MaterialIntent,
    MaterialOutcome,
    MaterialOutcomeStatus,
    ProjectionStatus,
    validate_header_against_identity,
)
from virtual_factory.factory.integration.material_bridge import (
    MaterialBridge,
    read_ledger_header,
)
from virtual_factory.factory.integration.outbox_projection import (
    PROJECTION_MODULE_ID,
    PROJECTION_MODULE_VERSION,
    OutboxProjectionModule,
)

__all__ = [
    "CHECKPOINT_SCHEMA_VERSION",
    "BridgeCheckpoint",
    "BridgeCheckpointError",
    "BridgeContractError",
    "BridgeError",
    "BridgeIdentity",
    "BridgeIdentityError",
    "BridgePolicy",
    "BridgeProjectionError",
    "BridgeRecoveryRequired",
    "BridgeStateError",
    "MaterialIntent",
    "MaterialOutcome",
    "MaterialOutcomeStatus",
    "ProjectionStatus",
    "validate_header_against_identity",
    "build_bridge_checkpoint",
    "validate_bridge_checkpoint",
    "MaterialBridge",
    "read_ledger_header",
    "PROJECTION_MODULE_ID",
    "PROJECTION_MODULE_VERSION",
    "OutboxProjectionModule",
]
