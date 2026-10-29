"""Shared data contracts. Evaluation labels never enter feature tables."""
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class DatasetBundle:
    tables: dict[str, pd.DataFrame]
    truth: dict[str, pd.DataFrame] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def copy(self) -> "DatasetBundle":
        return DatasetBundle(
            {k: v.copy(deep=True) for k, v in self.tables.items()},
            {k: v.copy(deep=True) for k, v in self.truth.items()},
            dict(self.metadata),
        )


PRIMARY_KEYS = {
    "customers": "customer_id", "products": "product_id", "suppliers": "supplier_id",
    "categories": "category_id", "orders": "order_id", "order_lines": "line_id",
    "sales": "sale_id", "inventory": "inventory_id", "stock_movements": "movement_id",
    "customer_sources": "record_id", "product_sources": "record_id", "supplier_sources": "record_id",
}

FOREIGN_KEYS = {
    "products": [("category_id", "categories", "category_id"), ("supplier_id", "suppliers", "supplier_id")],
    "orders": [("customer_id", "customers", "customer_id")],
    "order_lines": [("order_id", "orders", "order_id"), ("product_id", "products", "product_id")],
    "sales": [("order_id", "orders", "order_id")],
    "inventory": [("product_id", "products", "product_id")],
    "stock_movements": [("product_id", "products", "product_id")],
}
