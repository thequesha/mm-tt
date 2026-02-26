from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import verify_token
from app.database import get_db
from app.models import Car
from app.schemas import CarsListResponse, CarResponse

router = APIRouter(prefix="/api", tags=["cars"])


@router.get("/cars", response_model=CarsListResponse)
def get_cars(
    brand: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    min_year: Optional[int] = Query(None),
    max_year: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user_id: int = Depends(verify_token),
):
    query = db.query(Car)

    if brand:
        query = query.filter(Car.brand.ilike(f"%{brand}%"))
    if model:
        query = query.filter(Car.model.ilike(f"%{model}%"))
    if color:
        query = query.filter(Car.color.ilike(f"%{color}%"))
    if min_price is not None:
        query = query.filter(Car.price >= min_price)
    if max_price is not None:
        query = query.filter(Car.price <= max_price)
    if min_year is not None:
        query = query.filter(Car.year >= min_year)
    if max_year is not None:
        query = query.filter(Car.year <= max_year)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return CarsListResponse(
        items=[CarResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
    )
