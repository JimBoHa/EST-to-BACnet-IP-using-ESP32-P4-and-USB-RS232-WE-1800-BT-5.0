"""Versioned application records. These are not EST ECP frames or SDU exports."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

CONDITIONS = ("alarm", "trouble", "supervisory", "disabled")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Address(Model):
    network: str = Field(min_length=1, max_length=64)
    node: str = Field(min_length=1, max_length=64)
    point: str = Field(min_length=1, max_length=64)


class Device(Model):
    logical_device_id: str
    source_address: Address
    source_type: str = Field(min_length=1, max_length=64)
    source_label: str = Field(max_length=4096)
    supported_conditions: list[Literal["alarm", "trouble", "supervisory", "disabled"]] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def validate_identity(self):
        if str(UUID(self.logical_device_id)) != self.logical_device_id:
            raise ValueError("canonical UUID required")
        if len(set(self.supported_conditions)) != len(self.supported_conditions):
            raise ValueError("duplicate condition")
        for value in (self.source_label, self.source_type, *self.source_address.model_dump().values()):
            if "\x00" in value:
                raise ValueError("NUL is not permitted")
        return self


class Catalog(Model):
    schema_version: Literal[1] = 1
    source_mode: Literal["simulation"]
    fixture_only: Literal[True]
    site_id: str = Field(min_length=1, max_length=64)
    revision: int = Field(ge=1)
    declared_complete: Literal[True]
    declared_count: int = Field(ge=0, le=1000)
    devices: list[Device] = Field(max_length=1000)
    approved_retirements: bool = False
    identity_decisions: dict[str, Literal["same_logical_replacement", "new_identity"]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_catalog(self):
        if len(self.devices) != self.declared_count:
            raise ValueError("incomplete count")
        ids = [d.logical_device_id for d in self.devices]
        addresses = [d.source_address.model_dump_json() for d in self.devices]
        if len(set(ids)) != len(ids) or len(set(addresses)) != len(addresses):
            raise ValueError("duplicate identity/address")
        return self


class Record(Model):
    sequence: int = Field(ge=1, le=2**53-1)
    record_type: Literal["event", "snapshot", "history_gap", "diagnostic", "heartbeat"]
    logical_device_id: str | None = None
    binding_epoch: int | None = Field(default=None, ge=1)
    normalized_condition: Literal["alarm", "trouble", "supervisory", "disabled", "unknown"] = "unknown"
    transition: Literal["assert", "restore", "unknown"] = "unknown"
    values: dict[str, bool] = Field(default_factory=dict)
    raw_source_code: str = Field(default="", max_length=128)
    source_label_snapshot: str = Field(default="", max_length=4096)
    source_address: Address | None = None
    received_utc: str | None = Field(default=None, max_length=40)
    source_time: str | None = Field(default=None, max_length=40)
    time_quality: str = Field(default="monotonic_only", max_length=40)
    monotonic_ms: int = Field(default=0, ge=0)
    missing_sequence_start: int | None = Field(default=None, ge=1)
    missing_sequence_end: int | None = Field(default=None, ge=1)
    reason: str = Field(default="", max_length=512)

    @model_validator(mode="after")
    def validate_record(self):
        if self.record_type == "history_gap":
            a, b = self.missing_sequence_start, self.missing_sequence_end
            if a is None or b is None or not (a <= b < self.sequence) or b-a > 1000000 or not self.reason:
                raise ValueError("invalid explicit gap")
        elif self.missing_sequence_start is not None or self.missing_sequence_end is not None:
            raise ValueError("gap fields require history_gap")
        if not set(self.values) <= set(CONDITIONS):
            raise ValueError("unsupported condition key")
        if self.record_type == "snapshot" and (not self.values or not self.logical_device_id):
            raise ValueError("snapshot requires device and values")
        return self


class Batch(Model):
    schema_version: Literal[1] = 1
    gateway_id: str = Field(min_length=1, max_length=64)
    boot_id: str = Field(min_length=1, max_length=64)
    source_mode: Literal["simulation", "protocol_disabled"]
    sent_monotonic_ms: int | None = Field(default=None, ge=0)
    records: list[Record] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_batch(self):
        if self.source_mode == "protocol_disabled" and any(r.record_type in ("event", "snapshot") for r in self.records):
            raise ValueError("real state decoding is disabled")
        if len({r.sequence for r in self.records}) != len(self.records):
            raise ValueError("duplicate batch sequence")
        if self.sent_monotonic_ms is not None and any(r.monotonic_ms>self.sent_monotonic_ms for r in self.records):
            raise ValueError("observation timestamp is after batch timestamp")
        return self
