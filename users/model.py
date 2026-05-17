import hashlib
from typing import Optional

from pydantic import BaseModel, ValidationInfo, field_validator


class User(BaseModel):
    id: str
    api_key: Optional[str]

    _already_hashed: bool = False

    @field_validator("api_key", mode="before")
    @classmethod
    def hash_api_key(cls, value: Optional[str], info: Optional[ValidationInfo] = None) -> Optional[str]:
        if value is None:
            return None

        if info and info.context and info.context.get("already_hashed"):
            return value

        return hashlib.sha256(value.encode()).hexdigest()

    def is_api_user(self) -> bool:
        return bool(self.api_key)
    
    def __hash__(self) -> int:
        return self.id.__hash__()

