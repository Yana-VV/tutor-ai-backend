from pydantic import BaseModel, ConfigDict, field_serializer
from typing import List, Optional


class IssueItem(BaseModel):
    level: str
    message: str

    model_config = ConfigDict(from_attributes=True)


class DocumentItem(BaseModel):
    name: str
    detected_type: Optional[str] = None
    size_kb: int

    model_config = ConfigDict(from_attributes=True)


class ExtractedData(BaseModel):
    child_code: Optional[str] = None
    tutor: Optional[str] = None
    date: Optional[str] = None
    observed_blocks: Optional[str] = None


class CheckResponse(BaseModel):
    check_id: str
    status: str
    status_label: Optional[str] = None
    reason: Optional[str] = None
    issues: List[IssueItem] = []
    documents: List[DocumentItem] = []
    extracted: Optional[ExtractedData] = None
    checked_at: str

    model_config = ConfigDict(from_attributes=True)


class CheckListItem(BaseModel):
    id: str
    checked_at: str
    record_type: str
    status: str
    documents_count: int
