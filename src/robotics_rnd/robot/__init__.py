"""Generic robot contracts and platform-owned models."""

from .commands import CommandKind, RobotCommand
from .interface import RobotCapability, RobotInterface
from .journal import JournalRecord, RobotJournal, read_journal
from .models import (
    ConnectionState,
    FaultCategory,
    FaultSeverity,
    JointState,
    RobotFaultRecord,
    RobotMetadata,
    RobotMode,
    RobotState,
)
from .results import (
    CommandLifecycleEvent,
    CommandStatus,
    RobotResult,
    StatusEvidence,
    validate_command_transition,
)
from .service import RobotApplicationEvent, RobotApplicationService, RobotApplicationState

__all__ = [
    "CommandKind",
    "CommandLifecycleEvent",
    "CommandStatus",
    "ConnectionState",
    "FaultCategory",
    "FaultSeverity",
    "JointState",
    "JournalRecord",
    "RobotApplicationEvent",
    "RobotApplicationService",
    "RobotApplicationState",
    "RobotCapability",
    "RobotCommand",
    "RobotFaultRecord",
    "RobotInterface",
    "RobotJournal",
    "RobotMetadata",
    "RobotMode",
    "RobotResult",
    "RobotState",
    "StatusEvidence",
    "read_journal",
    "validate_command_transition",
]
