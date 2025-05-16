from typing import Any

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class Tokens(BaseModel):
    jwt_access: str
    jwt_refresh: str
