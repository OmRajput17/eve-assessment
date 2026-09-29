from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, SignupRequest


class AuthService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)

    def signup(self, data: SignupRequest) -> User:
        if self._users.get_by_email(data.email):
            raise ConflictError("Email already registered")

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            is_admin=data.email in {e.lower() for e in get_settings().admin_emails},
        )
        try:
            self._users.add(user)
            self._db.commit()
        except IntegrityError:  # two signups racing with the same email
            self._db.rollback()
            raise ConflictError("Email already registered")
        return user

    def login(self, data: LoginRequest) -> str:
        user = self._users.get_by_email(data.email)
        # Same message for "no such user" and "wrong password": don't reveal which emails exist.
        if user is None or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        return create_access_token(user.id)