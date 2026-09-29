from sqlalchemy import select

from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalars(select(User).where(User.email == email)).first()

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user