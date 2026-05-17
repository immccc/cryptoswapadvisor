from typing import Optional

from sqlalchemy import Engine
from sqlmodel import Session, delete, select
from users.db.repository import UsersRepository
from users.db.sql._mapping import map_user
from users.db.sql.model import User as UserSQLModel
from users.model import User


class UsersSQLRepository(UsersRepository):
    engine: Engine

    def __init__(self, engine: Engine):
        self.engine = engine

    def add_user(self, id: str, api_key: Optional[str]):
        with Session(self.engine) as session:
            session.merge(
                UserSQLModel(
                    id=str(id),
                    api_key=api_key,
                )
            )
            session.commit()


    def remove_user(self, id: str):
        with Session(self.engine) as session:
            session.exec(delete(UserSQLModel).where(UserSQLModel.id == str(id)))
            session.commit()


    def get_all_users(self) -> set[User]:
        with Session(self.engine) as session:
            users = session.exec(select(UserSQLModel)).all()
            return {
                map_user(user) for user in users
            }

    def get_by_api_key(self, api_key: str) -> Optional[User]:
        with Session(self.engine) as session:
            user = session.exec(
                select(UserSQLModel).where(UserSQLModel.api_key == api_key)
            ).first()

            if user:
                return map_user(user)
