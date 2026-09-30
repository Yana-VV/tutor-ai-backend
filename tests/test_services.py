import pytest
from fastapi import UploadFile
import io
from app.services import detect_document_type, validate_documents


def create_mock_file(filename: str, content: bytes = b"dummy") -> UploadFile:
    file = UploadFile(filename=filename, file=io.BytesIO(content))
    file.size = len(content)
    return file


# ==========================================
# БЛОК 1: Тесты логики определения типа файла
# ==========================================


@pytest.mark.parametrize(
    "filename, expected_type",
    [
        ("Дневник наблюдений.xlsx", "observation_diary"),
        ("Отчет о занятии.docx", "tutor_report"),
        ("Обратная связь родителя.pdf", "parent_feedback"),
        ("Заключение специалиста.jpg", "specialist_report"),
        ("ОТЧЁТ_О_ЗАНЯТИИ_15-03.docx", "tutor_report"),
        ("дневник___наблюдений-15.03.xlsx", "observation_diary"),
        ("  обратная   связь родителя  .png", "parent_feedback"),
        ("какой-то_файл.jpg", None),
        ("непонятный документ.pdf", None),
    ],
)
def test_detect_document_type(filename, expected_type):
    assert detect_document_type(filename) == expected_type


# ==========================================
# БЛОК 2: Тесты формирования итогового статуса
# ==========================================


@pytest.mark.asyncio
async def test_validate_daily_complete_happy_path():
    files = [
        create_mock_file("дневник наблюдений.xlsx"),
        create_mock_file("отчет о занятии.docx"),
        create_mock_file("обратная связь родителя.pdf"),
    ]

    docs, issues, status, status_label, reason = await validate_documents(
        files, "daily"
    )

    assert status == "complete"
    assert len(issues) == 0
    assert len(docs) == 3


@pytest.mark.asyncio
async def test_validate_weekly_complete_happy_path():
    files = [
        create_mock_file("дневник наблюдений.xlsx"),
        create_mock_file("отчет о занятии.docx"),
        create_mock_file("обратная связь родителя.pdf"),
        create_mock_file("заключение специалиста.pdf"),
    ]

    docs, issues, status, status_label, reason = await validate_documents(
        files, "weekly"
    )

    assert status == "complete"
    assert len(issues) == 0


@pytest.mark.asyncio
async def test_validate_daily_incomplete_missing_file():
    files = [
        create_mock_file("дневник наблюдений.xlsx"),
        create_mock_file("обратная связь родителя.pdf"),
    ]

    docs, issues, status, status_label, reason = await validate_documents(
        files, "daily"
    )

    assert status == "incomplete"
    assert len(issues) == 1
    assert issues[0]["level"] == "error"
    assert "отчёт о занятии" in issues[0]["message"].lower()


@pytest.mark.asyncio
async def test_validate_weekly_incomplete_missing_specialist():
    files = [
        create_mock_file("дневник наблюдений.xlsx"),
        create_mock_file("отчет о занятии.docx"),
        create_mock_file("обратная связь родителя.pdf"),
    ]

    docs, issues, status, status_label, reason = await validate_documents(
        files, "weekly"
    )

    assert status == "incomplete"
    assert any(
        "заключение специалиста" in i["message"].lower()
        for i in issues
        if i["level"] == "error"
    )


@pytest.mark.asyncio
async def test_validate_unknown_file_creates_warning():
    files = [
        create_mock_file("дневник наблюдений.xlsx"),
        create_mock_file("отчет о занятии.docx"),
        create_mock_file("обратная связь родителя.pdf"),
        create_mock_file("странная_картинка.png"),
    ]

    docs, issues, status, status_label, reason = await validate_documents(
        files, "daily"
    )

    assert status == "complete"
    assert len(issues) == 1
    assert issues[0]["level"] == "warning"
    assert "не удалось определить тип" in issues[0]["message"].lower()


@pytest.mark.asyncio
async def test_validate_invalid_extension_error():
    files = [
        create_mock_file("дневник наблюдений.xlsx"),
        create_mock_file("отчет о занятии.docx"),
        create_mock_file("обратная связь родителя.pdf"),
        create_mock_file("дополнительно.txt"),
    ]

    docs, issues, status, status_label, reason = await validate_documents(
        files, "daily"
    )

    assert status == "incomplete"
    assert any(
        "Недопустимый формат файла" in i["message"]
        for i in issues
        if i["level"] == "error"
    )


@pytest.mark.asyncio
async def test_validate_file_size_exceeded_error():
    large_content = b"0" * (20 * 1024 * 1024 + 1)

    files = [
        create_mock_file("дневник наблюдений.xlsx"),
        create_mock_file("отчет о занятии.docx"),
        create_mock_file("обратная связь родителя.pdf"),
        create_mock_file("тяжелое_фото.jpg", content=large_content),
    ]

    docs, issues, status, status_label, reason = await validate_documents(
        files, "daily"
    )

    assert status == "incomplete"
    assert any(
        "превышает 20 МБ" in i["message"] for i in issues if i["level"] == "error"
    )
