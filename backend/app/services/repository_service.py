from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.schemas.repository import RepositoryCreate


class RepositoryService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: RepositoryCreate) -> Repository:
        repo = Repository(**data.model_dump())
        self.db.add(repo)
        self.db.commit()
        self.db.refresh(repo)
        return repo

    def list_all(self) -> list[Repository]:
        stmt = select(Repository).order_by(Repository.created_at.desc())
        return list(self.db.scalars(stmt))