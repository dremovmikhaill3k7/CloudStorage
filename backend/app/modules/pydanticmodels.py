from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_admin: bool


class UserShow(BaseModel):
    username: str
    email: EmailStr
    storage_max: int
    storage_used: int
    is_admin: bool


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserCreate(BaseModel):
    username: str 
    password: str
    email: EmailStr
    is_admin: Optional[bool] = False


class DataToken(BaseModel):
    username: str


class Folder(BaseModel):
    name: str
    parent_folder_id: int
    user_id: int


class NewFolder(BaseModel):
    name: str


class File(BaseModel):
    name: str
    path: str
    weight: int
    owner_id: int
    folder_id: int


class FileUpdate(BaseModel):
    name: Optional[str] = None
    parent_folder_id: Optional[int] = None

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_folder_id: Optional[int] = None


class FolderInfo(BaseModel):
    id: int
    name: str
    weight: Optional[int] = None


class FileInfo(BaseModel):
    id: int
    name: str
    weight: int


class FolderContentResponse(BaseModel):
    current_folder: Optional[FolderInfo]
    folder_parent_id: Optional[int] = None
    subfolders: List[FolderInfo] = []
    files: List[FileInfo] = []


class Token(BaseModel):
    access_token: str
    token_type:str
    expired: datetime