from sqlalchemy import select
from sqlalchemy.orm import Session

from db.connect import engine
from db.models import Promocode


def main() -> None:
    with Session(engine) as session:
        rows = session.execute(select(Promocode.name).order_by(Promocode.id.asc())).all()
        for (name,) in rows:
            if name is None:
                continue
            print(name)


if __name__ == "__main__":
    main()


