"""Public Access File management service."""

from __future__ import annotations

import uuid

from immigration_compliance.models.paf import (
    PAFDocument,
    PAFDocumentType,
    PAFStatus,
    PublicAccessFile,
)


class PAFService:
    """Manages Public Access Files for H-1B/H-1B1/E-3 workers."""

    def __init__(self) -> None:
        self._pafs: dict[str, PublicAccessFile] = {}

    def create_paf(self, paf: PublicAccessFile) -> PublicAccessFile:
        # Auto-create required document placeholders if empty
        if not paf.documents:
            paf.documents = self._create_required_placeholders(paf.id)
        paf.status = self._compute_status(paf)
        self._pafs[paf.id] = paf
        return paf

    def get_paf(self, paf_id: str) -> PublicAccessFile | None:
        return self._pafs.get(paf_id)

    def get_paf_by_employee(self, employee_id: str) -> list[PublicAccessFile]:
        return [p for p in self._pafs.values() if p.employee_id == employee_id]

    def list_pafs(self) -> list[PublicAccessFile]:
        return list(self._pafs.values())

    def update_paf_document(
        self, paf_id: str, doc_type: PAFDocumentType, is_present: bool, title: str = "", notes: str = ""
    ) -> PublicAccessFile | None:
        paf = self._pafs.get(paf_id)
        if paf is None:
            return None

        for doc in paf.documents:
            if doc.document_type == doc_type:
                doc.is_present = is_present
                if title:
                    doc.title = title
                if notes:
                    doc.notes = notes
                break
        else:
            paf.documents.append(PAFDocument(
                id=str(uuid.uuid4()),
                paf_id=paf_id,
                document_type=doc_type,
                title=title or doc_type.value,
                is_present=is_present,
                notes=notes,
            ))

        paf.status = self._compute_status(paf)
        self._pafs[paf_id] = paf
        return paf

    def delete_paf(self, paf_id: str) -> bool:
        return self._pafs.pop(paf_id, None) is not None

    def _create_required_placeholders(self, paf_id: str) -> list[PAFDocument]:
        required = [
            (PAFDocumentType.LCA_CERTIFIED, "Certified Labor Condition Application"),
            (PAFDocumentType.PREVAILING_WAGE_DETERMINATION, "Prevailing Wage Determination"),
            (PAFDocumentType.ACTUAL_WAGE_MEMO, "Actual Wage Documentation"),
            (PAFDocumentType.WAGE_SYSTEM_EXPLANATION, "Wage System Explanation Memo"),
            (PAFDocumentType.LCA_POSTING_NOTICE, "LCA Posting Notice / Proof of Posting"),
        ]
        return [
            PAFDocument(
                id=str(uuid.uuid4()),
                paf_id=paf_id,
                document_type=dt,
                title=title,
                is_present=False,
            )
            for dt, title in required
        ]

    def _compute_status(self, paf: PublicAccessFile) -> PAFStatus:
        score = paf.completeness_score
        if score >= 100.0:
            return PAFStatus.COMPLETE
        if score >= 60.0:
            return PAFStatus.NEEDS_REVIEW
        return PAFStatus.INCOMPLETE
