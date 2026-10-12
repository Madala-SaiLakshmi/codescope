from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.repository import RepositoryCreate, RepositoryRead
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


def get_service(db: Session = Depends(get_db)) -> RepositoryService:
    return RepositoryService(db)


@router.post("", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
def register_repository(
    payload: RepositoryCreate,
    user: User = Depends(get_current_user),
    service: RepositoryService = Depends(get_service),
):
    return service.create(payload, user.id)


@router.get("", response_model=list[RepositoryRead])
def list_repositories(
    user: User = Depends(get_current_user),
    service: RepositoryService = Depends(get_service),
):
    return service.list_for_owner(user.id)
