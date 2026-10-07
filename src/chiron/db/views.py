import argparse
from pathlib import Path

from sqlalchemy import create_engine

from chiron.config import PROJECT_ROOT, get_settings
from chiron.db.session import normalize_database_url


def apply_views(sql_path: Path | None = None) -> None:
    path = sql_path or PROJECT_ROOT / "powerbi" / "views.sql"
    sql = path.read_text(encoding="utf-8")
    engine = create_engine(normalize_database_url(get_settings().database_url), pool_pre_ping=True)
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Power BI SQL views")
    parser.add_argument("--sql", type=Path, default=None)
    args = parser.parse_args()
    apply_views(args.sql)


if __name__ == "__main__":
    main()
