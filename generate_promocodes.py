import random
import string
import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.connect import engine
from db.models import Base, Promocode, init_db


RUSSIAN_UPPER = [
    "А", "Б", "В", "Г", "Д", "Е", "Ё", "Ж", "З", "И", "Й",
    "К", "Л", "М", "Н", "О", "П", "Р", "С", "Т", "У", "Ф",
    "Х", "Ц", "Ч", "Ш", "Щ", "Ъ", "Ы", "Ь", "Э", "Ю", "Я",
]


def generate_code() -> str:
    digits = string.digits
    letters = RUSSIAN_UPPER
    # pattern: 0A00A
    return (
        random.choice(digits)
        + random.choice(letters)
        + random.choice(digits)
        + random.choice(digits)
        + random.choice(letters)
    )


def main() -> None:
    init_db()

    generated: set[str] = set()

    with Session(engine) as session:
        # Ensure uniqueness against DB too
        existing_names = set(
            name for (name,) in session.execute(select(Promocode.name)).all()
        )

        while len(generated) < 100:
            code = generate_code()
            if code in generated or code in existing_names:
                continue
            generated.add(code)

        now_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        objects = [
            Promocode(name=code, has_activated=False) for code in sorted(generated)
        ]

        # Base.created_at is defaulted, but set explicitly to same timestamp if desired
        # Leaving default in place for clarity and consistency with other models

        session.add_all(objects)
        session.commit()

    print(f"Inserted {len(generated)} promo codes.")


if __name__ == "__main__":
    main()


