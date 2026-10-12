import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import AnalysisJob
from app.models.impact import ImpactReport
from app.models.repository import Repository
from app.models.user import User
from app.security import decode_token

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise _unauthorized()
    try:
        user_id = int(decode_token(creds.credentials)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _unauthorized()
    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized()
    return user


# Resources of other users look exactly like missing ones (404), so ids cannot be probed.
def owned_repository(db: Session, user: User, repository_id: int) -> Repository:
    repo = db.get(Repository, repository_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def owned_job(db: Session, user: User, job_id: int) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id)
    repo = db.get(Repository, job.repository_id) if job else None
    if job is None or repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return job


def owned_report(db: Session, user: User, report_id: int) -> ImpactReport:
    report = db.get(ImpactReport, report_id)
    repo = db.get(Repository, report.repository_id) if report else None
    if report is None or repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Impact report not found")
    return report
