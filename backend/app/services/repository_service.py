from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.schemas.repository import RepositoryCreate


class RepositoryService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: RepositoryCreate, owner_id: int) -> Repository:
        repo = Repository(**data.model_dump(), owner_id=owner_id)
        self.db.add(repo)
        self.db.commit()
        self.db.refresh(repo)
        return repo

    def list_for_owner(self, owner_id: int) -> list[Repository]:
        stmt = (select(Repository).where(Repository.owner_id == owner_id)
                .order_by(Repository.created_at.desc(), Repository.id.desc()))
        return list(self.db.scalars(stmt))
