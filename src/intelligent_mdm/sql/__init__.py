"""DuckDB queries run in a per-call isolated connection with external access disabled."""
import re
from importlib.resources import files
from threading import Timer

import duckdb
import pandas as pd

from intelligent_mdm.models import DatasetBundle

QUERY_NAMES = ("monthly_sales", "customer_summary", "product_performance", "category_margin",
               "repeat_customers", "price_history")


def query_text(name: str) -> str:
    if name not in QUERY_NAMES:
        raise ValueError("Unknown analytical query")
    return files(__package__).joinpath(f"{name}.sql").read_text(encoding="utf-8")


def query(bundle: DatasetBundle, sql: str, limit: int = 10000, timeout: float = 8.) -> pd.DataFrame:
    if not 1 <= limit <= 100000:
        raise ValueError("Result limit must be between 1 and 100000")
    with duckdb.connect(config={"enable_external_access": False, "threads": 2, "memory_limit": "512MB"}) as conn:
        for name, frame in bundle.tables.items():
            if not re.fullmatch(r"[a-z_]+", name):
                raise ValueError("Unsafe table identifier")
            conn.register(name, frame)
        # This view is a line-level fact table with exactly one invoice per order.
        conn.execute("""CREATE VIEW fulfilled_lines AS
            SELECT l.*, o.customer_id, o.order_date
            FROM order_lines l JOIN orders o USING(order_id)
            JOIN sales s USING(order_id) WHERE o.status = 'fulfilled'""")
        statements = conn.extract_statements(sql)
        if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
            raise ValueError("Only a single SELECT / WITH query is supported")
        timer = Timer(timeout, conn.interrupt)
        try:
            timer.start()
            return conn.execute(f"SELECT * FROM ({sql.strip().rstrip(';')}) AS result LIMIT {int(limit)}").df()
        except duckdb.Error as exc:
            raise ValueError(f"Analytical query failed: {exc}") from exc
        finally:
            timer.cancel()


def run_named(bundle: DatasetBundle, name: str) -> pd.DataFrame:
    return query(bundle, query_text(name))
