from pydantic import BaseModel


class UserRegistrationRequest(BaseModel):
    email: str
