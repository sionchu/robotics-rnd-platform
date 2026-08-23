"""Portable, redacted JSONL journal for robot application evidence and replay."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from robotics_rnd.core import FrameId
from robotics_rnd.core.geometry import Pose, Quaternion, Vector3

from .models import (
    ConnectionState,
    FaultCategory,
    FaultSeverity,
    JointState,
    RobotFaultRecord,
    RobotMode,
    RobotState,
)
from .results import CommandStatus, RobotResult, StatusEvidence

JOURNAL_SCHEMA = "robotics-rnd.robot-journal"
JOURNAL_SCHEMA_VERSION = 1
_SENSITIVE_KEY_PARTS = ("host", "address", "ip", "token", "secret", "password", "serial")


def _redacted_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def to_jsonable(value: Any, *, key: str = "") -> Any:
    if key and _redacted_key(key):
        return "<redacted>"
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: to_jsonable(getattr(value, item.name), key=item.name) for item in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(item_key): to_jsonable(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, tuple | list | set | frozenset):
        return [to_jsonable(item) for item in value]
    raise TypeError(f"value of type {type(value).__name__} is not journal-serializable")


@dataclass(frozen=True, slots=True)
class JournalRecord:
    sequence: int
    session_id: str
    event_type: str
    timestamp: datetime
    payload: Mapping[str, Any]


class RobotJournal:
    def __init__(self, path: Path, session_id: str) -> None:
        if not session_id.strip():
            raise ValueError("journal session_id is required")
        self.path = path
        self.session_id = session_id
        self._sequence = 0
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_type: str, payload: Mapping[str, Any]) -> JournalRecord:
        if not event_type.strip():
            raise ValueError("journal event_type is required")
        self._sequence += 1
        timestamp = datetime.now(UTC)
        clean_payload = to_jsonable(payload)
        document = {
            "schema": JOURNAL_SCHEMA,
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "sequence": self._sequence,
            "session_id": self.session_id,
            "event_type": event_type,
            "timestamp": timestamp.isoformat(),
            "payload": clean_payload,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n")
        assert isinstance(clean_payload, dict)
        return JournalRecord(self._sequence, self.session_id, event_type, timestamp, clean_payload)

    def record_state(self, state: RobotState, reason: str) -> JournalRecord:
        return self.append("state", {"reason": reason, "state": state})

    def record_command(self, command_id: str, command: object) -> JournalRecord:
        return self.append("command_submitted", {"command_id": command_id, "command": command})

    def record_result(self, command_kind: str, result: RobotResult) -> JournalRecord:
        return self.append("command_result", {"command_kind": command_kind, "result": result})

    def record_transition(
        self, command_id: str, status: CommandStatus, evidence: StatusEvidence, message: str = ""
    ) -> JournalRecord:
        return self.append(
            "command_transition",
            {
                "command_id": command_id,
                "status": status,
                "evidence": evidence,
                "message": message,
            },
        )


def read_journal(path: Path) -> Iterator[JournalRecord]:
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            document = json.loads(line)
            if document.get("schema") != JOURNAL_SCHEMA:
                raise ValueError(f"journal line {line_number} has an unknown schema")
            if document.get("schema_version") != JOURNAL_SCHEMA_VERSION:
                raise ValueError(f"journal line {line_number} has an unsupported schema version")
            timestamp = datetime.fromisoformat(document["timestamp"])
            if timestamp.tzinfo is None:
                raise ValueError(f"journal line {line_number} has a naive timestamp")
            yield JournalRecord(
                int(document["sequence"]),
                str(document["session_id"]),
                str(document["event_type"]),
                timestamp,
                document["payload"],
            )


def state_from_json(payload: Mapping[str, Any]) -> RobotState:
    joints_payload = payload["joints"]
    pose_payload = payload["tool_pose"]
    position_payload = pose_payload["position_m"]
    orientation_payload = pose_payload["orientation"]
    fault_payload = payload.get("fault")
    fault = None
    if fault_payload:
        fault = RobotFaultRecord(
            FaultCategory(fault_payload["category"]),
            FaultSeverity(fault_payload["severity"]),
            str(fault_payload["code"]),
            str(fault_payload["message"]),
            datetime.fromisoformat(fault_payload["occurred_at"]),
            bool(fault_payload["recoverable"]),
            str(fault_payload.get("source", "platform")),
            fault_payload.get("raw_vendor_context", {}),
        )
    return RobotState(
        connected=bool(payload["connected"]),
        mode=RobotMode(payload["mode"]),
        joints=JointState(
            tuple(str(value) for value in joints_payload["names"]),
            tuple(float(value) for value in joints_payload["positions_rad"]),
            (
                tuple(float(value) for value in joints_payload["velocities_rad_s"])
                if joints_payload.get("velocities_rad_s") is not None
                else None
            ),
        ),
        tool_pose=Pose(
            Vector3(
                float(position_payload["x"]),
                float(position_payload["y"]),
                float(position_payload["z"]),
            ),
            Quaternion(
                float(orientation_payload["x"]),
                float(orientation_payload["y"]),
                float(orientation_payload["z"]),
                float(orientation_payload["w"]),
            ),
            FrameId(str(pose_payload["frame"]["value"])),
        ),
        timestamp=datetime.fromisoformat(payload["timestamp"]),
        fault_message=payload.get("fault_message"),
        connection_state=ConnectionState(payload["connection_state"]),
        source_timestamp=(
            datetime.fromisoformat(payload["source_timestamp"]) if payload.get("source_timestamp") else None
        ),
        task_state=payload.get("task_state"),
        speed_ratio=float(payload["speed_ratio"]) if payload.get("speed_ratio") is not None else None,
        digital_inputs=tuple(bool(value) for value in payload.get("digital_inputs", [])),
        digital_outputs=tuple(bool(value) for value in payload.get("digital_outputs", [])),
        fault=fault,
    )


def result_from_json(payload: Mapping[str, Any]) -> RobotResult:
    return RobotResult(
        bool(payload["success"]),
        str(payload["message"]),
        state_from_json(payload["state"]),
        str(payload["command_id"]) if payload.get("command_id") is not None else None,
        CommandStatus(payload["status"]),
        StatusEvidence(payload["status_evidence"]),
        datetime.fromisoformat(payload["started_at"]) if payload.get("started_at") else None,
        datetime.fromisoformat(payload["completed_at"]) if payload.get("completed_at") else None,
        str(payload["error_code"]) if payload.get("error_code") is not None else None,
        payload.get("diagnostics", {}),
        str(payload["vendor_code"]) if payload.get("vendor_code") is not None else None,
    )
