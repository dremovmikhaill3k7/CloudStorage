from typing import Annotated
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
import os
from app.auth.config import DB_USER
from app.modules.modules import User


engine = create_async_engine(url=DB_USER ,echo=True)
async_session = async_sessionmaker(bind=engine)

async def getdb():
    async with async_session() as session:
        yield session


async def get_user(username: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()