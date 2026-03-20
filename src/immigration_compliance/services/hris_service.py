"""HRIS integration service."""

from __future__ import annotations

import uuid
from datetime import datetime

from immigration_compliance.models.hris import (
    FieldMapping,
    HRISIntegration,
    HRISProvider,
    IntegrationStatus,
    SyncDirection,
    SyncRecord,
)


# Pre-configured field mappings per provider
_DEFAULT_MAPPINGS: dict[HRISProvider, list[dict]] = {
    HRISProvider.WORKDAY: [
        {"hris_field": "Worker_ID", "immigration_field": "id", "is_required": True},
        {"hris_field": "Legal_First_Name", "immigration_field": "first_name", "is_required": True},
        {"hris_field": "Legal_Last_Name", "immigration_field": "last_name", "is_required": True},
        {"hris_field": "Email_Address", "immigration_field": "email", "is_required": True},
        {"hris_field": "Organization", "immigration_field": "department"},
        {"hris_field": "Job_Profile_Name", "immigration_field": "job_title"},
        {"hris_field": "Hire_Date", "immigration_field": "hire_date"},
        {"hris_field": "Country_of_Citizenship", "immigration_field": "country_of_citizenship", "is_required": True},
        {"hris_field": "Visa_Type", "immigration_field": "visa_type", "is_required": True},
        {"hris_field": "Visa_Expiration_Date", "immigration_field": "visa_expiration_date"},
        {"hris_field": "Work_Location_City", "immigration_field": "worksite_city"},
        {"hris_field": "Work_Location_State", "immigration_field": "worksite_state"},
        {"hris_field": "Annual_Salary", "immigration_field": "actual_wage"},
    ],
    HRISProvider.ADP: [
        {"hris_field": "associateOID", "immigration_field": "id", "is_required": True},
        {"hris_field": "person.legalName.givenName", "immigration_field": "first_name", "is_required": True},
        {"hris_field": "person.legalName.familyName1", "immigration_field": "last_name", "is_required": True},
        {"hris_field": "businessCommunication.emailUri", "immigration_field": "email", "is_required": True},
        {"hris_field": "organizationalUnit.nameLong", "immigration_field": "department"},
        {"hris_field": "job.jobTitle", "immigration_field": "job_title"},
        {"hris_field": "workerDates.originalHireDate", "immigration_field": "hire_date"},
        {"hris_field": "person.citizenshipCountryCode", "immigration_field": "country_of_citizenship", "is_required": True},
        {"hris_field": "workLocation.address.cityName", "immigration_field": "worksite_city"},
        {"hris_field": "workLocation.address.stateCode", "immigration_field": "worksite_state"},
        {"hris_field": "compensation.basePayAmount", "immigration_field": "actual_wage"},
    ],
    HRISProvider.BAMBOOHR: [
        {"hris_field": "id", "immigration_field": "id", "is_required": True},
        {"hris_field": "firstName", "immigration_field": "first_name", "is_required": True},
        {"hris_field": "lastName", "immigration_field": "last_name", "is_required": True},
        {"hris_field": "workEmail", "immigration_field": "email", "is_required": True},
        {"hris_field": "department", "immigration_field": "department"},
        {"hris_field": "jobTitle", "immigration_field": "job_title"},
        {"hris_field": "hireDate", "immigration_field": "hire_date"},
        {"hris_field": "country", "immigration_field": "country_of_citizenship", "is_required": True},
        {"hris_field": "city", "immigration_field": "worksite_city"},
        {"hris_field": "state", "immigration_field": "worksite_state"},
    ],
    HRISProvider.SAP_SUCCESSFACTORS: [
        {"hris_field": "userId", "immigration_field": "id", "is_required": True},
        {"hris_field": "firstName", "immigration_field": "first_name", "is_required": True},
        {"hris_field": "lastName", "immigration_field": "last_name", "is_required": True},
        {"hris_field": "email", "immigration_field": "email", "is_required": True},
        {"hris_field": "department", "immigration_field": "department"},
        {"hris_field": "jobTitle", "immigration_field": "job_title"},
        {"hris_field": "hireDate", "immigration_field": "hire_date"},
        {"hris_field": "countryOfBirth", "immigration_field": "country_of_citizenship", "is_required": True},
    ],
}


class HRISService:
    """Manages HRIS integrations and data sync."""

    def __init__(self) -> None:
        self._integrations: dict[str, HRISIntegration] = {}
        self._sync_records: list[SyncRecord] = []

    def create_integration(self, integration: HRISIntegration) -> HRISIntegration:
        # Apply default mappings if none provided
        if not integration.field_mappings and integration.provider in _DEFAULT_MAPPINGS:
            integration.field_mappings = [
                FieldMapping(**m) for m in _DEFAULT_MAPPINGS[integration.provider]
            ]
        self._integrations[integration.id] = integration
        return integration

    def get_integration(self, integration_id: str) -> HRISIntegration | None:
        return self._integrations.get(integration_id)

    def list_integrations(self) -> list[HRISIntegration]:
        return list(self._integrations.values())

    def update_status(self, integration_id: str, status: IntegrationStatus, error: str = "") -> HRISIntegration | None:
        integration = self._integrations.get(integration_id)
        if integration is None:
            return None
        updated = integration.model_copy(update={
            "status": status,
            "error_message": error,
            "updated_at": datetime.utcnow(),
        })
        self._integrations[integration_id] = updated
        return updated

    def delete_integration(self, integration_id: str) -> bool:
        return self._integrations.pop(integration_id, None) is not None

    def simulate_sync(self, integration_id: str) -> SyncRecord:
        """Simulate a sync operation (would connect to real API in production)."""
        integration = self._integrations.get(integration_id)
        record = SyncRecord(
            id=str(uuid.uuid4()),
            integration_id=integration_id,
            status="completed",
            completed_at=datetime.utcnow(),
            records_processed=integration.employee_count if integration else 0,
            records_created=0,
            records_updated=integration.employee_count if integration else 0,
            records_failed=0,
        )
        self._sync_records.append(record)

        if integration:
            updated = integration.model_copy(update={
                "status": IntegrationStatus.CONNECTED,
                "last_sync": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
            self._integrations[integration_id] = updated

        return record

    def get_sync_records(self, integration_id: str | None = None) -> list[SyncRecord]:
        records = self._sync_records
        if integration_id:
            records = [r for r in records if r.integration_id == integration_id]
        return sorted(records, key=lambda r: r.started_at, reverse=True)

    def get_default_mappings(self, provider: HRISProvider) -> list[FieldMapping]:
        mappings = _DEFAULT_MAPPINGS.get(provider, [])
        return [FieldMapping(**m) for m in mappings]

    @property
    def supported_providers(self) -> list[dict]:
        return [
            {"id": p.value, "name": p.value.replace("_", " ").title(), "has_default_mappings": p in _DEFAULT_MAPPINGS}
            for p in HRISProvider
        ]
