from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Integer, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import bcrypt

from app.database import Base

class User(Base):
    """
    User account model to store registration details, login credentials,
    and associated state. Includes secure hashing helper methods.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    projects: Mapped[List["Project"]] = relationship(
        "Project", 
        back_populates="owner", 
        cascade="all, delete-orphan"
    )

    def verify_password(self, password: str) -> bool:
        """Verifies a plaintext password against the stored hashed password."""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                self.hashed_password.encode("utf-8")
            )
        except Exception:
            return False

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hashes a plaintext password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


class Project(Base):
    """
    Project model encapsulating a set of parsed papers, isolated per-user.
    """
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True) # UUID representation
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    papers: Mapped[List["AcademicPaper"]] = relationship(
        "AcademicPaper", 
        back_populates="project", 
        cascade="all, delete-orphan"
    )


class AcademicPaper(Base):
    """
    AcademicPaper model representing metadata, parser statistics,
    and PDF file storage info for parsed literature.
    """
    __tablename__ = "academic_papers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True) # UUID representation
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pages_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    processed_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="papers")
    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", 
        back_populates="paper", 
        cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """
    ChatMessage model representing chat history exchanges
    conducted on specific parsed papers.
    """
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("academic_papers.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False) # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    paper: Mapped["AcademicPaper"] = relationship("AcademicPaper", back_populates="chat_messages")
