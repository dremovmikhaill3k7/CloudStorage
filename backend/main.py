from datetime import datetime, timedelta
from typing import Annotated
import uuid
from fastapi.responses import FileResponse
from fastapi import Body, Depends, FastAPI, HTTPException, Query, UploadFile, logger, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi import File as FileUp
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.auth import authenticate_user, create_token, get_current_admin, get_current_user
from app.auth.utils_auth import get_password_hash
from app.auth.config import ACCESS_TOKEN_EXPIRE_MINUTES, STORAGE
from app.modules.modules import File, Folder, User
from app.modules.pydanticmodels import FileUpdate, FolderContentResponse, FolderUpdate, NewFolder, Token, UserCreate, UserShow, UserUpdate
from app.modules.pydanticmodels import User as SUser
from app.utils.utils import calculate_folder_weight, delete_parent_weights, get_files_and_folders, update_parent_folders_weight, update_parent_weights
from app.database.database import getdb
import os



app = FastAPI() 

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        '*',
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

@app.get('/api/admin/users')
async def get_all_user(db: AsyncSession = Depends(getdb), current_user: User = Depends(get_current_admin)) -> list[SUser]:
    result = await db.execute(select(User))
    if not result:
        raise HTTPException(status_code=404, detail="Users not found")
    
    users = result.scalars().all()

    return [SUser.model_validate(user.__dict__) for user in users]

# Работа с аккаунтом пользователя
@app.get('/api/user/')
async def get_user(db: AsyncSession = Depends(getdb), current_user: User = Depends(get_current_user)) -> UserShow:
    result = await db.execute(select(User).where(current_user.id == User.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='User not found')
    return UserShow.model_validate(user.__dict__)


@app.patch('/api/user/')
async def update_user(db: AsyncSession = Depends(getdb), 
                      current_user: User = Depends(get_current_user), 
                      request: UserUpdate = Body(...)):
    result = await db.execute(select(User).where(current_user.id == User.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='User not found')
    update_values = request.model_dump(exclude_unset=True)

    if not update_values:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No data to update")
    
    if "password" in update_values:
        update_values["password"] = get_password_hash(update_values["password"])
    
    for field, value in update_values.items():
        setattr(user, field, value)
 
    await db.commit()
    await db.refresh(user)
    
    return user
    

@app.post('/api/user/create')
async def create_user(db: AsyncSession = Depends(getdb), request: UserCreate = Body(...)):
    try:
        exist = await db.execute(
            select(User).where(
                (request.email == User.email) |
                (request.username == User.username)
            )
        )
        if exist.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        hashed_password = await get_password_hash(request.password)

        db_user = User(
            username = request.username,
            password = hashed_password,
            email = request.email,
            is_admin = request.is_admin
        )

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        user = await db.execute(select(User).where(User.username == request.username))
        user_res = user.scalar()

        db_folder = Folder(
            name = 'disk',
            parent_folder_id = None,
            user_id = user_res.id
        )

        db.add(db_folder)
        await db.commit()
        await db.refresh(db_folder)

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expires_at = datetime.now() + access_token_expires
        access_token = await create_token(
        data={"sub": request.username, "is_admin": request.is_admin}, expires_delta=access_token_expires
        )

        return {
            **request.model_dump(),
            "access_token": access_token,
            "token type": "bearer",
            "expire": expires_at
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Работа с папками

@app.get('/api/client/disk/')
async def get_start_folder(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(getdb)
):
    root_folder = await db.execute(select(Folder).where(
        Folder.user_id == current_user.id,
        Folder.parent_folder_id == None
    ))
    root = root_folder.scalar()

    if not root_folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Folder not found")

    return await get_files_and_folders(user_id = current_user.id, folder_id=root.id, folder_name=root.name,db=db)


@app.get('/api/client/folder/{idfolder}')
async def get_folder(
    idfolder: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession =Depends(getdb)
):
    
    folder = await db.scalar(select(Folder).where(
        Folder.id == idfolder,
        Folder.user_id == current_user.id
    ))

    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Folder not found")

    return await get_files_and_folders(user_id=current_user.id, folder_id=idfolder, folder_name=folder.name, folder_parent_id=folder.parent_folder_id ,db=db)


@app.delete('/api/client/folder/{idfolder}')
async def delete_folder(
    idfolder: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(getdb)
):
    try:
        folder = await db.scalar(
            select(Folder)
            .where(
                Folder.user_id == current_user.id,
                Folder.id == idfolder
            )
            .with_for_update()
        )
        if not folder:
            raise HTTPException(404, "Folder not found")

        all_files = []
        all_folders = []

        async def gather_nested(folder_id: int):
            folders = (await db.scalars(
                select(Folder)
                .where(Folder.parent_folder_id == folder_id)
            )).all()
            
            for child_folder in folders:
                all_folders.append(child_folder)
                await gather_nested(child_folder.id)
                
            files = (await db.scalars(
                select(File)
                .where(File.folderid == folder_id)
            )).all()
            all_files.extend(files)

        await gather_nested(idfolder)
        all_folders.append(folder)
        
        total_size = sum(f.weight for f in all_files)

        for file in all_files:
            try:
                if os.path.exists(file.path):
                    os.remove(file.path)
            except Exception as e:
                await db.rollback()
                raise HTTPException(500, f"Error deleting file {file.path}: {str(e)}")
            await db.delete(file)

        for f in all_folders:
            await db.delete(f)

        user = await db.get(User, current_user.id)
        user.storage_used -= total_size

        if folder.parent_folder_id:
            await update_parent_folders_weight(db, folder.id, -total_size)

        await db.commit()
        return {"code": 200, "status": "Deleted"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Folder deletion error: {str(e)}")
        raise HTTPException(500, "Deletion failed")


@app.get("/api/resolve-path/{path:path}")
async def resolve_path(
    path: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(getdb)
):
    path_parts = [p for p in path.split("/") if p]
    current_parent_id = None

    for folder_name in path_parts:
        folder = await db.scalar(
            select(Folder.id)
            .where(
                Folder.user_id == current_user.id,
                Folder.name == folder_name,
                Folder.parent_folder_id == current_parent_id
            )
        )
        if not folder:
            raise HTTPException(404, "Folder not found")
        current_parent_id = folder

    return {"folder_id": current_parent_id}


@app.post('/api/client/folder/{folder_parent_id}')
async def add_new_folder(
    folder_parent_id: int,
    current_user: User = Depends(get_current_user),
    request: NewFolder = Body(...),
    db: AsyncSession = Depends(getdb)
):
    
    parent_folder_id = await db.scalar(select(Folder).where(
        Folder.id == folder_parent_id
    ))
    
    if not parent_folder_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Folder already exists")


    existing_stmt = select(Folder).where(
        Folder.user_id == current_user.id,
        Folder.name == request.name,
        Folder.parent_folder_id == folder_parent_id
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Folder already exists")

    new_folder = Folder(
        name=request.name,
        user_id=current_user.id,
        parent_folder_id=folder_parent_id
    )
    db.add(new_folder)
    await db.commit()
    await db.refresh(new_folder)

    return {
        'id': new_folder.id,
        'name': new_folder.name,
        'parent_id': new_folder.parent_folder_id,
        'status': 'created'
    }


@app.patch('/api/client/folder/{idfolder}')
async def folder_update(
    idfolder: int,
    current_user: User = Depends(get_current_user),
    update_data: FolderUpdate = Body(...),
    db: AsyncSession = Depends(getdb)
):
    target_folder = await db.scalar(
        select(Folder)
        .where(
            Folder.id == idfolder,
            Folder.user_id == current_user.id
        )
        .with_for_update()
    )

    if not target_folder:
        raise HTTPException(404, "Folder not found")

    old_parent_id = target_folder.parent_folder_id
    old_weight = await calculate_folder_weight(db, target_folder.id)

    update_values = update_data.model_dump(exclude_unset=True)
    new_parent_id = update_values.get('parent_folder_id', target_folder.parent_folder_id)

    if new_parent_id is not None:
        new_parent = await db.scalar(
            select(Folder)
            .where(Folder.id == new_parent_id, Folder.user_id == current_user.id)
        )
        if not new_parent:
            raise HTTPException(404, "New parent folder not found")
        
        current_parent = new_parent
        while current_parent:
            if current_parent.id == target_folder.id:
                raise HTTPException(400, "Cannot move folder to its own subfolder")
            current_parent = await db.get(Folder, current_parent.parent_folder_id)

    parent_condition = (
        Folder.parent_folder_id == new_parent_id 
        if new_parent_id is not None 
        else Folder.parent_folder_id.is_(None)
    )
    
    existing_folder = await db.scalar(
        select(Folder)
        .where(
            Folder.name == update_values.get('name', target_folder.name),
            parent_condition,
            Folder.user_id == current_user.id,
            Folder.id != target_folder.id
        )
    )

    if existing_folder:
        raise HTTPException(400, "Folder with this name already exists in target directory")

    if old_parent_id != new_parent_id:
        if old_parent_id is not None:
            await update_parent_folders_weight(db, old_parent_id, -old_weight)
        
        if new_parent_id is not None:
            await update_parent_folders_weight(db, new_parent_id, old_weight)
        else:
            target_folder.weight = old_weight

    for field, value in update_values.items():
        setattr(target_folder, field, value)

    try:
        await db.commit()
        await db.refresh(target_folder)
        return target_folder
    except Exception as e:
        await db.rollback()
        if old_parent_id != new_parent_id:
            if old_parent_id is not None:
                await update_parent_folders_weight(db, old_parent_id, old_weight)
            if new_parent_id is not None:
                await update_parent_folders_weight(db, new_parent_id, -old_weight)
        raise HTTPException(500, f"Error updating folder: {str(e)}")


# Работа с файлами
@app.post('/api/file/upload/{folderid}')
async def upload_file(folderid: int,
                      file: UploadFile = FileUp(...), 
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(getdb)):
    filesize = file.size

    user = await db.execute(
        select(User)
        .where(User.id == current_user.id)
        .with_for_update()
    )
    user = user.scalar_one()

    folder = await db.scalar(select(Folder).where(Folder.id == folderid))

    if user.storage_used + filesize > user.storage_max:
        raise HTTPException(status_code=400, detail="Not enough storage space")
    
    exist_file = await db.scalar(select(File).where(
        File.name == file.filename,
        File.folderid == folderid
    ))

    if exist_file:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File is exist")
    
    try:
        file_id = str(uuid.uuid4())
        file_path = os.path.join(STORAGE, file_id)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        new_file = File(name = file.filename,
                        path = file_path,
                        weight = filesize,
                        ownerid = current_user.id,
                        folderid = folderid)
        
        db.add(new_file)
        user.storage_used += filesize
        await update_parent_weights(db, folder.id, filesize)
        await db.commit()
        await db.refresh(new_file)

        return {"Status": f"File {file_id} created", "Code": "200"}

        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get('/api/file/download/{file_id}')
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(getdb)
):
    file_result = await db.scalar(select(File).where(
        File.ownerid == current_user.id,
        File.id == file_id
    ))

    if not file_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if not os.path.exists(file_result.path):
        await db.delete(file_result)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not detected in storage, file was deleted from DB')

    return FileResponse(file_result.path,
                        filename=file_result.name)


@app.delete('/api/file/delete/{file_id}')
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(getdb)
):
    file_exist = await db.scalar(select(File).where(File.id == file_id,
                                                    File.ownerid == current_user.id))
    if not file_exist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    
    user = await db.scalar(select(User).where(User.id == current_user.id))
    folder = await db.scalar(select(Folder).where(Folder.id == file_exist.folderid))
    
    await db.delete(file_exist)
    try:
        os.remove(file_exist.path)
    except Exception as e:
        pass
    user.storage_used -= file_exist.weight
    await delete_parent_weights(db, folder.id, file_exist.weight)
    await db.commit()
    await db.refresh(user)


@app.patch('/api/file/update/{file_id}')
async def file_update(
    file_id: int,
    current_user: User = Depends(get_current_user),
    update_data: FileUpdate = Body(...),
    db: AsyncSession = Depends(getdb)
):
    target_file = await db.scalar(
        select(File)
        .where(
            File.id == file_id,
            File.ownerid == current_user.id
        )
        .with_for_update()
    )
    if not target_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    old_folder_id = target_file.folderid
    file_weight = target_file.weight

    update_values = update_data.model_dump(exclude_unset=True)
    
    if 'parent_folder_id' in update_values:
        update_values['folderid'] = update_values.pop('parent_folder_id')

    new_name = update_values.get('name', target_file.name)
    new_folder_id = update_values.get('folderid', target_file.folderid)

    if 'folderid' in update_values and new_folder_id is not None:
        new_folder = await db.scalar(
            select(Folder)
            .where(
                Folder.id == new_folder_id,
                Folder.user_id == current_user.id
            )
        )
        if not new_folder:
            raise HTTPException(404, detail="Target folder not found")

    folder_condition = (
        File.folderid == new_folder_id 
        if new_folder_id is not None 
        else File.folderid.is_(None))
    
    existing_file = await db.scalar(
        select(File)
        .where(
            File.name == new_name,
            folder_condition,
            File.ownerid == current_user.id,
            File.id != file_id,
        )
    )
    if existing_file:
        raise HTTPException(400, "File with this name already exists in target directory")

    if new_folder_id != old_folder_id:
        if old_folder_id is not None:
            await update_parent_folders_weight(db, old_folder_id, -file_weight)
        if new_folder_id is not None:
            await update_parent_folders_weight(db, new_folder_id, file_weight)

    for field, value in update_values.items():
        setattr(target_file, field, value)

    try:
        await db.commit()
        await db.refresh(target_file)
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, detail=f"Error updating file: {str(e)}")

    return target_file


# Работа с токеном
@app.post('/api/token') 
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(getdb)
) -> Token:
    user = await authenticate_user(form_data.username, form_data.password, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_token(
        data={"sub": user.username, "is_admin": user.is_admin}, expires_delta=access_token_expires
    )
    expires_at = datetime.now() + access_token_expires
    return Token(access_token=access_token, token_type="bearer", expired=expires_at)