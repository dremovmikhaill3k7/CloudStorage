from sqlalchemy import Column, String, Integer, ForeignKey, Float, BigInteger, Boolean, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    email = Column(String, unique=True)
    storage_max = mapped_column(BigInteger, default=21474836480)
    storage_used = mapped_column(BigInteger, default=0)
    is_admin = Column(Boolean)
    
    files = relationship("File", back_populates='user', cascade="all, delete-orphan")
    folders = relationship("Folder", back_populates='user', cascade="all, delete-orphan")


class Folder(Base):
    __tablename__ = 'folder'

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String, nullable=False)
    parent_folder_id = mapped_column(Integer, ForeignKey('folder.id', ondelete='CASCADE'))
    user_id = mapped_column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    weight = mapped_column(BigInteger,default=0, server_default=text("0"))
    
    user = relationship("User", back_populates='folders')
    parent_folder = relationship("Folder", back_populates="subfolders", remote_side=[id])
    subfolders = relationship("Folder", back_populates="parent_folder")
    files = relationship("File", back_populates='folder', cascade="all, delete-orphan")


class File(Base):
    __tablename__ = 'file'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    weight = Column(Integer, nullable=False)
    ownerid = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))
    folderid = Column(Integer, ForeignKey('folder.id', ondelete='CASCADE'))
    
    user = relationship("User", back_populates="files")
    folder = relationship('Folder', back_populates='files')