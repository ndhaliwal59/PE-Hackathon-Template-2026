"""One-shot: create tables and load app/data/*.csv. Run: uv run load_seed.py"""

from app import create_app
from app.database import db
from app.models import Event, Url, User
from app.seed import load_csv_seed


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_tables([User, Url, Event], safe=True)
        load_csv_seed(skip_if_populated=True)
        print(
            f"Seed done: users={User.select().count()}, "
            f"urls={Url.select().count()}, events={Event.select().count()}"
        )


if __name__ == "__main__":
    main()
