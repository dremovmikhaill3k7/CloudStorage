from typing import Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.modules.modules import File, Folder
from app.modules.pydanticmodels import FileInfo, FolderContentResponse, FolderInfo
import aiofiles


async def get_files_and_folders(user_id: int, folder_id: int, folder_name: str, db: AsyncSession, folder_parent_id: int = None):
    result_folders = await db.execute(select(Folder).where(
        Folder.parent_folder_id == folder_id,
        Folder.user_id == user_id
    ))
    folders = result_folders.scalars().all()

    result_files = await db.execute(select(File).where(
        File.ownerid == user_id,
        File.folderid == folder_id
    ))
    files = result_files.scalars().all()

    return FolderContentResponse(current_folder=FolderInfo(id=folder_id, name=folder_name),
                                 folder_parent_id=folder_parent_id,
                                subfolders=[FolderInfo(id=folder.id, name=folder.name, weight = folder.weight) for folder in folders],
                                files=[FileInfo(id=file.id, name=file.name, weight=file.weight) for file in files])


async def update_parent_weights(db: AsyncSession, folder_id: int, delta: int):
    current_folder = await db.scalar(select(Folder).where(Folder.id == folder_id))
    while current_folder:
        current_folder.weight += delta
        await db.flush() 
        current_folder = await db.scalar(select(Folder).where(Folder.id == current_folder.parent_folder_id))
    
    await db.commit()


async def calculate_folder_weight(db: AsyncSession, folder_id: int) -> int:
    total_weight = 0
    files = await db.scalars(select(File).where(File.folderid == folder_id))
    total_weight += sum(file.weight for file in files.all())

    subfolders = await db.scalars(select(Folder).where(Folder.parent_folder_id == folder_id))
    for subfolder in subfolders.all():
        total_weight += await calculate_folder_weight(db, subfolder.id)
    
    return total_weight


async def delete_parent_weights(db: AsyncSession, folder_id: int, delta: int):
    current_folder = await db.scalar(select(Folder).where(Folder.id == folder_id))
    while current_folder:
        current_folder.weight -= delta
        await db.flush() 
        current_folder = await db.scalar(select(Folder).where(Folder.id == current_folder.parent_folder_id))
    
    await db.commit()


async def update_parent_folders_weight(db: AsyncSession, folder_id: int, delta: int):
    current_folder = await db.get(Folder, folder_id)
    while current_folder:
        current_folder.weight += delta
        parent_id = current_folder.parent_folder_id
        if parent_id is None:
            break
        current_folder = await db.get(Folder, parent_id)
    await db.commit()