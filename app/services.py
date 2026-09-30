import os
import re
from typing import List, Tuple
from fastapi import UploadFile

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".jpg", ".png"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


def detect_document_type(filename: str) -> str | None:
    """Определяет тип документа по подстроке в имени файла."""

    normalized = filename.lower().replace("ё", "е")
    normalized_name = re.sub(r"[\s_-]+", " ", normalized)

    if "дневник наблюдений" in normalized_name:
        return "observation_diary"
    elif "отчёт о занятии" in normalized_name or "отчет о занятии" in normalized_name:
        return "tutor_report"
    elif "обратная связь родителя" in normalized_name:
        return "parent_feedback"
    elif "заключение специалиста" in normalized_name:
        return "specialist_report"

    return None


async def validate_documents(
    files: List[UploadFile], record_type: str
) -> Tuple[List[dict], List[dict], str, str, str]:
    """
    Проверяет загруженные файлы и возвращает кортеж:
    (список документов, список ошибок, итоговый статус, ярлык статуса, причина)
    """
    documents = []
    issues = []

    found_types = set()

    for file in files:
        filename = file.filename or "unknown_file"

        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)
        size_kb = size_bytes // 1024

        detected_type = detect_document_type(filename)
        if detected_type:
            found_types.add(detected_type)
        else:
            issues.append(
                {
                    "level": "warning",
                    "message": f"Не удалось определить тип материала: «{filename}»",
                }
            )

        if size_bytes > MAX_FILE_SIZE_BYTES:
            issues.append(
                {
                    "level": "error",
                    "message": f"Размер файла {filename} превышает 20 МБ",
                }
            )

        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            issues.append(
                {
                    "level": "error",
                    "message": f"Недопустимый формат файла {filename}. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}",
                }
            )

        documents.append(
            {"name": filename, "detected_type": detected_type, "size_kb": size_kb}
        )

    missing_docs = []

    if "observation_diary" not in found_types:
        missing_docs.append("дневник наблюдений")
    if "tutor_report" not in found_types:
        missing_docs.append("отчёт о занятии")
    if "parent_feedback" not in found_types:
        missing_docs.append("обратная связь родителя")

    if record_type == "weekly" and "specialist_report" not in found_types:
        missing_docs.append("заключение специалиста")

    for missing in missing_docs:
        issues.append(
            {
                "level": "error",
                "message": f"Отсутствует обязательный материал: {missing}",
            }
        )

    has_errors = any(issue["level"] == "error" for issue in issues)

    if has_errors:
        status = "incomplete"
        status_label = "Запись неполная — нельзя передавать в анализ"
        first_error = next(
            (i["message"] for i in issues if i["level"] == "error"), None
        )
        reason = first_error if first_error else "Найдены критические ошибки"
    else:
        status = "complete"
        status_label = "Запись полная — готова к анализу"
        reason = "Все необходимые материалы предоставлены"

    return documents, issues, status, status_label, reason
