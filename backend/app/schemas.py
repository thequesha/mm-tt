from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CarResponse(BaseModel):
    id: int
    brand: str
    model: str
    year: Optional[int] = None
    price: Optional[int] = None
    color: Optional[str] = None
    url: str

    class Config:
        from_attributes = True


class CarsListResponse(BaseModel):
    items: list[CarResponse]
    total: int
    page: int
    per_page: int
