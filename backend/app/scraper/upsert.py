from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Car


def upsert_cars(db: Session, cars_data: list[dict]) -> tuple[int, int, int, int]:
    """Upsert car listings into the database.
    Returns (inserted_count, updated_count, skipped_count, failed_count).
    """
    inserted = 0
    updated = 0
    skipped = 0
    failed = 0

    for data in cars_data:
        url = data.get("url")
        if not url:
            skipped += 1
            continue

        try:
            with db.begin_nested():
                existing = db.query(Car).filter(Car.url == url).first()
                if existing:
                    changed = False
                    for field in ("brand", "model", "year", "price", "color"):
                        new_val = data.get(field)
                        if new_val is not None and getattr(existing, field) != new_val:
                            setattr(existing, field, new_val)
                            changed = True
                    if changed:
                        existing.updated_at = datetime.utcnow()
                        updated += 1
                else:
                    car = Car(
                        brand=data.get("brand", ""),
                        model=data.get("model", ""),
                        year=data.get("year"),
                        price=data.get("price"),
                        color=data.get("color"),
                        url=url,
                    )
                    db.add(car)
                    inserted += 1

                # Force SQL execution inside nested transaction to catch bad rows early.
                db.flush()
        except Exception as e:
            failed += 1
            model_len = len(data.get("model") or "")
            print(
                f"[upsert] Skipping row url={url} model_len={model_len}: {e}"
            )
            continue

    db.commit()
    return inserted, updated, skipped, failed
