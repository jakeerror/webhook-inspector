from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

# Reusable dependency alias (FastAPI skill: prefer Annotated dependencies).
SessionDep = Annotated[AsyncSession, Depends(get_db)]
