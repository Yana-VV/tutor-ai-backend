import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Check(Base):
    """Таблица для хранения информации о самой проверке"""

    __tablename__ = "checks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    record_type = Column(String, nullable=False)  # daily или weekly
    status = Column(String, nullable=False, default="check_in_progress")
    status_label = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    extracted_data = Column(JSON, nullable=True)

    documents = relationship(
        "Document", back_populates="check", cascade="all, delete-orphan"
    )
    issues = relationship("Issue", back_populates="check", cascade="all, delete-orphan")


class Document(Base):
    """Таблица для сохранения информации о загруженных файлах"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    check_id = Column(String, ForeignKey("checks.id"))
    name = Column(String, nullable=False)
    detected_type = Column(String, nullable=True)
    size_kb = Column(Integer, nullable=False)

    check = relationship("Check", back_populates="documents")


class Issue(Base):
    """Таблица для сохранения найденных ошибок и предупреждений"""

    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    check_id = Column(String, ForeignKey("checks.id"))
    level = Column(String, nullable=False)
    message = Column(String, nullable=False)

    check = relationship("Check", back_populates="issues")
