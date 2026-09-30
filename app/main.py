from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from enum import Enum

from app.database import get_db
from app import models, schemas, services

app = FastAPI(title="Tutor AI Backend API")


class RecordType(str, Enum):
    daily = "daily"
    weekly = "weekly"


@app.post(
    "/api/checks",
    response_model=schemas.CheckResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_check(
    record_type: RecordType = Form(description="Тип записи"),
    files: List[UploadFile] = File(
        default=[], description="Список файлов для проверки"
    ),
    child_code: Optional[str] = Form(None),
    tutor: Optional[str] = Form(None),
    date: Optional[str] = Form(None),
    observed_blocks: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо загрузить хотя бы один файл",
        )

    docs_data, issues_data, final_status, status_label, reason = (
        await services.validate_documents(files, record_type.value)
    )

    extracted_dict = {
        "child_code": child_code,
        "tutor": tutor,
        "date": date,
        "observed_blocks": observed_blocks,
    }

    new_check = models.Check(
        record_type=record_type.value,
        status=final_status,
        status_label=status_label,
        reason=reason,
        extracted_data=extracted_dict,
    )
    db.add(new_check)
    db.flush()

    for doc in docs_data:
        new_doc = models.Document(
            check_id=new_check.id,
            name=doc["name"],
            detected_type=doc["detected_type"],
            size_kb=doc["size_kb"],
        )
        db.add(new_doc)

    for issue in issues_data:
        new_issue = models.Issue(
            check_id=new_check.id, level=issue["level"], message=issue["message"]
        )
        db.add(new_issue)

    db.commit()
    db.refresh(new_check)

    return schemas.CheckResponse(
        check_id=new_check.id,
        status=new_check.status,
        status_label=new_check.status_label,
        reason=new_check.reason,
        issues=new_check.issues,
        documents=new_check.documents,
        extracted=schemas.ExtractedData(**(new_check.extracted_data or {})),
        checked_at=new_check.checked_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


@app.get("/api/checks", response_model=List[schemas.CheckListItem])
def get_checks(db: Session = Depends(get_db)):
    """Получение списка всех проверок"""
    checks = db.query(models.Check).order_by(models.Check.checked_at.desc()).all()

    result = []
    for check in checks:
        doc_count = (
            db.query(models.Document)
            .filter(models.Document.check_id == check.id)
            .count()
        )
        result.append(
            schemas.CheckListItem(
                id=check.id,
                checked_at=check.checked_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                record_type=check.record_type,
                status=check.status,
                documents_count=doc_count,
            )
        )
    return result


@app.get("/api/checks/{check_id}", response_model=schemas.CheckResponse)
def get_check_by_id(check_id: str, db: Session = Depends(get_db)):
    """Получение детальной информации о конкретной проверке"""
    check = db.query(models.Check).filter(models.Check.id == check_id).first()

    if not check:
        raise HTTPException(status_code=404, detail="Проверка не найдена")

    return schemas.CheckResponse(
        check_id=check.id,
        status=check.status,
        status_label=check.status_label,
        reason=check.reason,
        issues=check.issues,
        documents=check.documents,
        extracted=schemas.ExtractedData(**(check.extracted_data or {})),
        checked_at=check.checked_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
