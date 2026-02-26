from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from bot.config import settings
from bot.models import Car

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def search_cars(filters: dict, limit: int = 10) -> list[Car]:
    """Search cars in the database based on filter parameters from LLM."""
    db: Session = SessionLocal()
    try:
        query = db.query(Car)

        brand = filters.get("brand")
        if brand:
            query = query.filter(Car.brand.ilike(f"%{brand}%"))

        model = filters.get("model")
        if model:
            query = query.filter(Car.model.ilike(f"%{model}%"))

        color = filters.get("color")
        if color:
            query = query.filter(Car.color.ilike(f"%{color}%"))

        min_price = filters.get("min_price")
        if min_price is not None:
            query = query.filter(Car.price >= int(min_price))

        max_price = filters.get("max_price")
        if max_price is not None:
            query = query.filter(Car.price <= int(max_price))

        min_year = filters.get("min_year")
        if min_year is not None:
            query = query.filter(Car.year >= int(min_year))

        max_year = filters.get("max_year")
        if max_year is not None:
            query = query.filter(Car.year <= int(max_year))

        results = query.limit(limit).all()
        return results
    finally:
        db.close()
