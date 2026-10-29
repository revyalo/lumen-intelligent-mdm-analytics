"""A fictional distributor with two years of coherent transactions and dirty source masters."""
import numpy as np
import pandas as pd

from intelligent_mdm.models import DatasetBundle

SIZES = {"demo": (120, 48, 1400), "large": (1800, 360, 24000)}
AS_OF = "2026-09-30"


def _sources(master: pd.DataFrame, key: str, departments: tuple[str, str], rng: np.random.Generator):
    records, labels = [], []
    for i, row in master.iterrows():
        for j, department in enumerate(departments):
            rec = row.to_dict()
            entity = rec.pop(key)
            # Remove foreign keys from observational source records; never expose label IDs to matching.
            rec.pop("category_id", None)
            rec.pop("supplier_id", None)
            rid = f"{key[:1].upper()}R{i:05d}-{j}"
            rec.update(record_id=rid, source=department)
            if j == 1:
                rec["name"] = "  " + str(rec["name"]).upper() + "  "
                if i % 4 == 0:
                    rec["name"] = rec["name"].replace("e", "").replace("E", "", 1)
                if "email" in rec:
                    if i % 5 == 0:
                        rec["email"] = None
                    elif i % 19 == 0:
                        rec["email"] = "invalid-email"
                if "phone" in rec:
                    rec["phone"] = "+34 " + str(rec["phone"])[-9:-6] + " " + str(rec["phone"])[-6:]
                if "tax_id" in rec and i % 7 == 0:
                    rec["tax_id"] = None
                if "tax_id" in rec and i % 29 == 0 and i > 0:
                    rec["tax_id"] = master.iloc[i-1]["tax_id"]
                if "region" in rec and i % 6 == 0:
                    rec["region"] = None
                if "unit_price" in rec and i % 11 == 0:
                    rec["unit_price"] = -float(rec["unit_price"])
                if i % 10 == 0:
                    rec["updated_at"] = pd.Timestamp("2023-01-01")
            records.append(rec)
            labels.append({"record_id": rid, "entity_id": entity})
        if i % 10 == 0:
            duplicate = dict(records[-2])
            duplicate["record_id"] += "-copy"
            records.append(duplicate)
            labels.append({"record_id": duplicate["record_id"], "entity_id": row[key]})
    frame = pd.DataFrame(records)
    # Deterministic seeded order prevents algorithms from exploiting adjacent duplicates.
    return frame.iloc[rng.permutation(len(frame))].reset_index(drop=True), pd.DataFrame(labels)


def generate(size: str = "demo", seed: int = 42) -> DatasetBundle:
    """Generate all amounts in EUR excluding tax; sales represent fulfilled order invoices."""
    if size not in SIZES:
        raise ValueError(f"size must be one of {list(SIZES)}")
    n, p, o = SIZES[size]
    rng = np.random.default_rng(seed)
    regions = np.array(["North", "South", "East", "West", "Central"])
    customers = pd.DataFrame({
        "customer_id": [f"C{i:05d}" for i in range(n)],
        "name": [f"{['Aster', 'Cobalt', 'Juniper', 'Solstice', 'Vela'][i % 5]} {['Studio', 'Supply', 'Works', 'Labs', 'Trading'][(i // 5) % 5]} {i:04d}" for i in range(n)],
        "tax_id": [f"SYN{i:08d}" for i in range(n)],
        "email": [f"accounts{i}@customer.example" for i in range(n)],
        "phone": [f"+3491{i:07d}" for i in range(n)],
        "region": rng.choice(regions, n),
        "created_at": pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 240, n), unit="D"),
        "updated_at": pd.Timestamp(AS_OF) - pd.to_timedelta(rng.integers(0, 200, n), unit="D"),
    })
    suppliers = pd.DataFrame({
        "supplier_id": [f"S{i:03d}" for i in range(12)],
        "name": [f"Lattice Supply {i:02d}" for i in range(12)],
        "tax_id": [f"VENDOR{i:05d}" for i in range(12)],
        "email": [f"orders{i}@supplier.example" for i in range(12)],
        "updated_at": pd.Timestamp(AS_OF),
    })
    categories = pd.DataFrame({"category_id": [f"K{i}" for i in range(4)],
                               "category": ["Office", "Packaging", "Safety", "Warehouse"]})
    cost = rng.uniform(2, 80, p).round(2)
    products = pd.DataFrame({
        "product_id": [f"P{i:04d}" for i in range(p)],
        "sku": [f"LUM-{i:05d}" for i in range(p)],
        "name": [f"{['Paper', 'Carton', 'Gloves', 'Label'][i % 4]} model {i:04d}" for i in range(p)],
        "category_id": [f"K{i % 4}" for i in range(p)],
        "supplier_id": rng.choice(suppliers.supplier_id, p),
        "unit_cost": cost,
        "unit_price": (cost * rng.uniform(1.15, 1.8, p)).round(2),
        "unit": "each", "updated_at": pd.Timestamp(AS_OF),
    })
    # Heavy-tailed demand, stable preferred category, and 10% structurally inactive accounts.
    weights = rng.pareto(1.8, n) + .25
    weights[int(n * .9):] = 0
    weights /= weights.sum()
    ci = rng.choice(n, o, p=weights)
    day = rng.integers(0, 730, o)
    dates = pd.Timestamp("2024-10-01") + pd.to_timedelta(day, unit="D")
    orders = pd.DataFrame({"order_id": [f"O{i:07d}" for i in range(o)],
                           "customer_id": customers.customer_id.to_numpy()[ci],
                           "order_date": dates,
                           "status": rng.choice(["fulfilled", "cancelled"], o, p=[.94, .06])})
    oi = np.repeat(np.arange(o), rng.integers(1, 6, o))
    pi = rng.integers(0, p, len(oi))
    preferred = (ci[oi] % 4 + 4 * rng.integers(0, p // 4, len(oi))).astype(int)
    pi = np.where(rng.random(len(oi)) < .65, preferred, pi)
    seasonal = np.where(pd.DatetimeIndex(dates[oi]).month.isin([11, 12]), 1.7, 1.0)
    quantity = np.maximum(1, (rng.poisson(4, len(oi)) * seasonal).astype(int))
    extreme = rng.choice(len(oi), max(1, len(oi)//200), replace=False)
    quantity[extreme] *= 25  # Legitimate synthetic bulk purchases, not injected accounting errors.
    prices = products.unit_price.to_numpy()[pi] * (1 + day[oi] / 730 * .12)
    discounts = rng.choice([0, .05, .10], len(oi), p=[.75, .2, .05])
    lines = pd.DataFrame({"line_id": [f"L{i:08d}" for i in range(len(oi))],
                          "order_id": orders.order_id.to_numpy()[oi],
                          "product_id": products.product_id.to_numpy()[pi],
                          "quantity": quantity, "unit_price": prices.round(2),
                          "unit_cost": products.unit_cost.to_numpy()[pi], "discount": discounts})
    lines["net_amount"] = (lines.quantity * lines.unit_price * (1-lines.discount)).round(2)
    totals = lines.groupby("order_id").net_amount.sum()
    sales = orders.loc[orders.status.eq("fulfilled"), ["order_id", "order_date"]].copy()
    sales["sale_id"] = [f"I{i:07d}" for i in range(len(sales))]
    sales["amount"] = sales.order_id.map(totals).round(2)
    sales = sales.rename(columns={"order_date": "sale_date"})
    # Inventory is an as-of balance: opening + receipts - fulfilled dispatches.
    shipped = lines[lines.order_id.isin(sales.order_id)].groupby("product_id").quantity.sum()
    inv = products[["product_id"]].copy()
    inv["inventory_id"] = [f"B{i:04d}" for i in range(p)]
    inv["warehouse"] = "Main"
    inv["opening_qty"] = 100
    inv["received_qty"] = inv.product_id.map(shipped).fillna(0).astype(int) + rng.integers(0, 200, p)
    inv["shipped_qty"] = inv.product_id.map(shipped).fillna(0).astype(int)
    inv["on_hand"] = inv.opening_qty + inv.received_qty - inv.shipped_qty
    inv["as_of"] = pd.Timestamp(AS_OF)
    movements = []
    for i, row in inv.iterrows():
        for kind, qty, date in [("opening", row.opening_qty, "2024-10-01"),
                                ("receipt", row.received_qty, "2024-10-01")]:
            movements.append({"movement_id": f"M{i}-{kind}", "product_id": row.product_id,
                              "warehouse": "Main", "movement_date": pd.Timestamp(date), "kind": kind, "quantity": qty})
    dispatch = lines[lines.order_id.isin(sales.order_id)].merge(orders[["order_id", "order_date"]], on="order_id")
    for row in dispatch.itertuples():
        movements.append({"movement_id": "M-"+row.line_id, "product_id": row.product_id,
                          "warehouse": "Main", "movement_date": row.order_date, "kind": "dispatch", "quantity": -row.quantity})
    cs, ct = _sources(customers, "customer_id", ("administration", "sales"), rng)
    ps, pt = _sources(products, "product_id", ("catalogue", "purchasing"), rng)
    ss, st = _sources(suppliers, "supplier_id", ("administration", "purchasing"), rng)
    return DatasetBundle(
        tables={"customers": customers, "customer_sources": cs, "products": products,
                "product_sources": ps, "suppliers": suppliers, "supplier_sources": ss,
                "categories": categories, "orders": orders, "order_lines": lines,
                "sales": sales, "inventory": inv, "stock_movements": pd.DataFrame(movements)},
        truth={"customer_sources": ct, "product_sources": pt, "supplier_sources": st,
               "bulk_purchases": pd.DataFrame({"line_id": lines.line_id,
                   "is_bulk": np.isin(np.arange(len(lines)), extreme)})},
        metadata={"company": "Lumen Distribution", "size": size, "seed": seed, "as_of": AS_OF,
                  "currency": "EUR", "period_start": "2024-10-01", "period_end": AS_OF,
                  "generator_version": 1, "synthetic": True},
    )
