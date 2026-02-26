from sqlalchemy import create_engine
from sqlalchemy import or_
from sqlalchemy.orm import sessionmaker, Session

from bot.config import settings
from bot.models import Car

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

BRAND_SEARCH_ALIASES = {
    "bmw": ["BMW", "БМВ", "ビーエム", "ＢＭＷ"],
    "toyota": ["Toyota", "Тойота", "トヨタ"],
    "honda": ["Honda", "Хонда", "ホンダ"],
    "nissan": ["Nissan", "Ниссан", "日産", "ニッサン"],
    "mercedes": ["Mercedes", "Benz", "Мерседес", "メルセデス", "ベンツ"],
    "audi": ["Audi", "Ауди", "アウディ"],
    "mazda": ["Mazda", "Мазда", "マツダ"],
    "subaru": ["Subaru", "Субару", "スバル"],
    "lexus": ["Lexus", "Лексус", "レクサス"],
}


def search_cars(
    filters: dict,
    limit: int = 10,
    brand_match_in_model: bool = False,
) -> list[Car]:
    """Search cars in the database based on filter parameters from LLM."""
    db: Session = SessionLocal()
    try:
        query = db.query(Car)

        brand = filters.get("brand")
        if brand:
            brand_value = str(brand).strip()
            aliases = BRAND_SEARCH_ALIASES.get(brand_value.lower(), [brand_value])
            brand_conditions = [Car.brand.ilike(f"%{alias}%") for alias in aliases]
            if brand_match_in_model:
                for alias in aliases:
                    brand_conditions.append(Car.model.ilike(f"%{alias}%"))
            query = query.filter(or_(*brand_conditions))

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
