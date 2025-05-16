from pydantic import BaseModel


class RegisterRequest(BaseModel):
    login: str
    password: str


class RegisterResponse(BaseModel):
    pass


class LoginRequest(BaseModel):
    login: str
    password: str


class Verify2faRequest(BaseModel):
    user_id: str
    opt_code: str
