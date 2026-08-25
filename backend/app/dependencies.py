"""FastAPI dependency providers."""

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.identity import User


def get_db_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_current_user(
    user_id: Annotated[str | None, Header(alias="X-Demo-User-ID")] = None,
    session: Session = Depends(get_db_session),
) -> User:
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing demo identity")
    try:
        parsed_id = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid demo identity") from exc

    user = session.get(User, parsed_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown demo identity")
    return user
