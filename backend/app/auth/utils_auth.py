from passlib.context import CryptContext


async def get_password_hash(password: str) -> str:
    pwd_context = CryptContext(['bcrypt'], deprecated="auto")
    return pwd_context.hash(password)


async def verify_password(password_for_v: str, hashed_password: str) -> bool:
    pwd_context = CryptContext(['bcrypt'], deprecated="auto")
    return pwd_context.verify(password_for_v, hashed_password)