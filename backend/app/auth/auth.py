from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database.database import getdb, get_user
from app.auth.utils_auth import verify_password
import jwt
from app.auth.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.modules import User
from app.modules.pydanticmodels import DataToken


oauth2_scheme =  OAuth2PasswordBearer(tokenUrl='api/token')


async def authenticate_user(username: str, password: str, db: AsyncSession):
    user = await get_user(username, db)
    if user is None:
        return  None
    if not await verify_password(password, user.password):
        return None
    return user


async def create_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode.update({'exp': expire, "is_admin": data.get("is_admin", False)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)
    return encoded_jwt


async def get_current_user(db: Annotated[AsyncSession, Depends(getdb)], token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        is_admin: bool = payload.get("is_admin", False)
        token_data = DataToken(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = await get_user(token_data.username, db)
    if user is None:
        raise credentials_exception
    
    user.is_admin = is_admin
    return user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)]
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user