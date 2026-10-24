"""Repository for chronological investigation case notes."""

from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.case_note import CaseNote


class CaseNoteRepository:
    """Encapsulates append-only operations for investigation case notes."""

    @staticmethod
    def get_by_id(db: Session, note_id: int) -> CaseNote | None:
        """Fetch a specific note by ID."""
        stmt = (
            select(CaseNote)
            .where(CaseNote.id == note_id)
            .options(selectinload(CaseNote.author))
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create(
        db: Session,
        case_id: int,
        author_id: int | None,
        author_name: str,
        author_email: str,
        author_role: str,
        body: str,
    ) -> CaseNote:
        """Create and persist an immutable investigation note."""
        note = CaseNote(
            case_id=case_id,
            author_id=author_id,
            author_name=author_name,
            author_email=author_email,
            author_role=author_role,
            body=body.strip(),
        )
        db.add(note)
        db.flush()
        return note

    @staticmethod
    def list_by_case(
        db: Session,
        case_id: int,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[CaseNote], int]:
        """Retrieve notes for a specific case in chronological order (oldest first)."""
        stmt = (
            select(CaseNote)
            .where(CaseNote.case_id == case_id)
            .order_by(asc(CaseNote.created_at), asc(CaseNote.id))
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = db.execute(count_stmt).scalar_one()

        stmt = (
            stmt.offset((page - 1) * page_size)
            .limit(page_size)
            .options(selectinload(CaseNote.author))
        )
        records = list(db.execute(stmt).scalars().all())
        return records, total_count
