"""Control plane for lifecycle management."""

import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from configs.config import Settings
from src.data_plane import TFIDFRetriever
from src.observability import EventLog, get_logger
from src.state import StateStore
from src.utils import compute_file_hash

logger = get_logger(__name__)


class LifecycleState(str, Enum):
    """Lifecycle states."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    VALIDATING = "validating"
    VALIDATED = "validated"
    OPERATING = "operating"
    RECONCILING = "reconciling"
    CHECKPOINTING = "checkpointing"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    ERROR = "error"


class ControlPlane:
    """Control plane for orchestrating system lifecycle."""

    def __init__(self, settings: Settings) -> None:
        """Initialize control plane."""
        self.settings = settings
        self.state = LifecycleState.UNINITIALIZED
        self.state_store: Optional[StateStore] = None
        self.event_log: Optional[EventLog] = None
        self.retriever: Optional[TFIDFRetriever] = None
        self.validation_hashes: Dict[str, str] = {}

        logger.info("Control plane created", state=self.state.value)

    def initialize(self) -> None:
        """Initialize all components."""
        try:
            self.state = LifecycleState.INITIALIZING
            logger.info("Initializing control plane")

            # Ensure directories exist
            self.settings.ensure_directories()

            # Initialize state store
            self.state_store = StateStore(self.settings.get_state_db_path())
            logger.info("State store initialized")

            # Initialize event log
            self.event_log = EventLog(self.settings.get_event_log_path())
            logger.info("Event log initialized")

            # Initialize retriever (will load index on first use)
            self.retriever = TFIDFRetriever(
                self.settings.get_index_path(),
                self.settings.get_manifest_path(),
            )
            logger.info("Retriever initialized")

            self.state = LifecycleState.INITIALIZED
            logger.info("Control plane initialized", state=self.state.value)

            # Log initialization event
            if self.event_log:
                self.event_log.log_event(
                    "lifecycle",
                    {"action": "initialize", "state": self.state.value},
                )

        except Exception as e:
            self.state = LifecycleState.ERROR
            logger.error(f"Initialization failed: {e}")
            raise

    def validate(self) -> bool:
        """Validate system state using hash checks."""
        try:
            self.state = LifecycleState.VALIDATING
            logger.info("Validating system state")

            validation_results = {}

            # Validate index file
            if self.settings.get_index_path().exists():
                index_hash = compute_file_hash(str(self.settings.get_index_path()))
                validation_results["index"] = index_hash
                self.validation_hashes["index"] = index_hash
                logger.info("Index validated", hash=index_hash[:8])
            else:
                logger.warning("Index file not found")
                validation_results["index"] = None

            # Validate manifest
            if self.settings.get_manifest_path().exists():
                manifest_hash = compute_file_hash(str(self.settings.get_manifest_path()))
                validation_results["manifest"] = manifest_hash
                self.validation_hashes["manifest"] = manifest_hash
                logger.info("Manifest validated", hash=manifest_hash[:8])
            else:
                logger.warning("Manifest file not found")
                validation_results["manifest"] = None

            # Check if required files exist
            all_valid = all(v is not None for v in validation_results.values())

            if all_valid:
                self.state = LifecycleState.VALIDATED
                logger.info("Validation successful", hashes=validation_results)
            else:
                # Reset to a stable state to avoid remaining stuck in VALIDATING
                self.state = LifecycleState.INITIALIZED
                logger.warning("Validation incomplete", results=validation_results)

            # Log validation event
            if self.event_log:
                self.event_log.log_event(
                    "lifecycle",
                    {
                        "action": "validate",
                        "state": self.state.value,
                        "results": validation_results,
                    },
                )

            return all_valid

        except Exception as e:
            self.state = LifecycleState.ERROR
            logger.error(f"Validation failed: {e}")
            return False

    def operate(self) -> None:
        """Enter operating state."""
        if self.state != LifecycleState.VALIDATED:
            logger.warning("Cannot operate without validation")
            return

        self.state = LifecycleState.OPERATING
        logger.info("Entering operating state")

        if self.event_log:
            self.event_log.log_event(
                "lifecycle",
                {"action": "operate", "state": self.state.value},
            )

    def reconcile(self) -> bool:
        """Reconcile system state by running validation."""
        try:
            self.state = LifecycleState.RECONCILING
            logger.info("Reconciling system state")

            # Run validation
            result = self.validate()

            if result:
                self.state = LifecycleState.OPERATING
            else:
                self.state = LifecycleState.ERROR

            logger.info("Reconciliation complete", success=result)

            if self.event_log:
                self.event_log.log_event(
                    "lifecycle",
                    {"action": "reconcile", "state": self.state.value, "success": result},
                )

            return result

        except Exception as e:
            self.state = LifecycleState.ERROR
            logger.error(f"Reconciliation failed: {e}")
            return False

    def checkpoint(self) -> Path:
        """Create a checkpoint of current state."""
        try:
            self.state = LifecycleState.CHECKPOINTING
            logger.info("Creating checkpoint")

            # Create checkpoint data
            timestamp = datetime.now(UTC).isoformat().replace(":", "-")
            checkpoint_file = self.settings.get_checkpoint_dir() / f"checkpoint_{timestamp}.json"

            checkpoint_data = {
                "timestamp": timestamp,
                "state": self.state.value,
                "validation_hashes": self.validation_hashes,
                "settings": {
                    "seed_salt": self.settings.seed_salt,
                    "time_bucket_seconds": self.settings.time_bucket_seconds,
                    "max_sentences": self.settings.max_sentences,
                    "top_k_retrieval": self.settings.top_k_retrieval,
                },
            }

            # Write checkpoint
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, indent=2)

            logger.info("Checkpoint created", path=str(checkpoint_file))

            # Restore operating state
            if self.state == LifecycleState.CHECKPOINTING:
                self.state = LifecycleState.OPERATING

            if self.event_log:
                self.event_log.log_event(
                    "lifecycle",
                    {"action": "checkpoint", "path": str(checkpoint_file)},
                )

            return checkpoint_file

        except Exception as e:
            logger.error(f"Checkpoint failed: {e}")
            raise

    def terminate(self) -> None:
        """Terminate control plane."""
        try:
            self.state = LifecycleState.TERMINATING
            logger.info("Terminating control plane")

            # Close state store
            if self.state_store:
                self.state_store.close()

            self.state = LifecycleState.TERMINATED
            logger.info("Control plane terminated")

            if self.event_log:
                self.event_log.log_event(
                    "lifecycle",
                    {"action": "terminate", "state": self.state.value},
                )

        except Exception as e:
            self.state = LifecycleState.ERROR
            logger.error(f"Termination failed: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get current control plane state."""
        return {
            "state": self.state.value,
            "validation_hashes": self.validation_hashes,
            "initialized": self.state != LifecycleState.UNINITIALIZED,
            "operating": self.state == LifecycleState.OPERATING,
        }
