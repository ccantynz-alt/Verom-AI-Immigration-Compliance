"""HRIS integration models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class HRISProvider(str, Enum):
    WORKDAY = "workday"
    ADP = "adp"
    SAP_SUCCESSFACTORS = "sap_successfactors"
    BAMBOOHR = "bamboohr"
    PAYLOCITY = "paylocity"
    UKG = "ukg"
    NAMELY = "namely"
    GUSTO = "gusto"
    RIPPLING = "rippling"
    CUSTOM_API = "custom_api"
    CSV_UPLOAD = "csv_upload"


class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    SYNCING = "syncing"
    PENDING_SETUP = "pending_setup"


class SyncDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class FieldMapping(BaseModel):
    """Mapping between HRIS field and Verom.ai field."""

    hris_field: str
    immigration_field: str
    transform: str = ""
    is_required: bool = False


class HRISIntegration(BaseModel):
    """Configuration for an HRIS integration."""

    id: str
    provider: HRISProvider
    name: str
    status: IntegrationStatus = IntegrationStatus.PENDING_SETUP
    sync_direction: SyncDirection = SyncDirection.INBOUND
    api_endpoint: str = ""
    last_sync: datetime | None = None
    sync_interval_minutes: int = 60
    field_mappings: list[FieldMapping] = Field(default_factory=list)
    employee_count: int = 0
    error_message: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SyncRecord(BaseModel):
    """Record of a sync operation."""

    id: str
    integration_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: str = "running"
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_failed: int = 0
    errors: list[str] = Field(default_factory=list)
