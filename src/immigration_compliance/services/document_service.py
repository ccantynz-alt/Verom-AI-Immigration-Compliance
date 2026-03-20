"""Document management service."""

from __future__ import annotations

import uuid
from datetime import date

from immigration_compliance.models.document import Document, DocumentCategory, DocumentStatus


class DocumentService:
    """Manages document storage and retrieval."""

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}

    def add_document(self, doc: Document) -> Document:
        self._documents[doc.id] = doc
        return doc

    def get_document(self, doc_id: str) -> Document | None:
        return self._documents.get(doc_id)

    def list_documents(
        self,
        employee_id: str | None = None,
        category: DocumentCategory | None = None,
        case_id: str | None = None,
    ) -> list[Document]:
        docs = list(self._documents.values())
        if employee_id:
            docs = [d for d in docs if d.employee_id == employee_id]
        if category:
            docs = [d for d in docs if d.category == category]
        if case_id:
            docs = [d for d in docs if d.case_id == case_id]
        return sorted(docs, key=lambda d: d.created_at, reverse=True)

    def delete_document(self, doc_id: str) -> bool:
        return self._documents.pop(doc_id, None) is not None

    def get_expiring_documents(self, within_days: int = 90, as_of: date | None = None) -> list[Document]:
        ref = as_of or date.today()
        results = []
        for doc in self._documents.values():
            if doc.status != DocumentStatus.ACTIVE:
                continue
            days = doc.days_until_expiration(ref)
            if days is not None and 0 < days <= within_days:
                results.append(doc)
        return sorted(results, key=lambda d: d.expiration_date or date.max)

    def get_expired_documents(self, as_of: date | None = None) -> list[Document]:
        ref = as_of or date.today()
        return [
            d for d in self._documents.values()
            if d.status == DocumentStatus.ACTIVE and d.expiration_date and d.expiration_date < ref
        ]

    @property
    def total_documents(self) -> int:
        return len(self._documents)
