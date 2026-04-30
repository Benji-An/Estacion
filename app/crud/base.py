"""Generic CRUD base class."""
from typing import Generic, TypeVar, Type
from sqlalchemy.orm import Session
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class CRUDBase(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int):
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, skip=0, limit=100):
        return db.query(self.model).offset(skip).limit(limit).all()
