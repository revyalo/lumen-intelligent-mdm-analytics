# Data contracts and generation

All data describe **Lumen Distribution**, a fictional B2B distributor. Emails use reserved `.example` domains. `SYN…`/`VENDOR…` identifiers are invented keys, not jurisdiction-valid tax identifiers. Units are `each`, currency is EUR, amounts exclude tax, the reference date is 2026-09-30. Never interpret these data as actual market evidence.

| Table | Grain / primary key | Relationships / important fields |
|---|---|---|
| customers | One operational customer / customer_id | region, created_at, updated_at, name, email, phone, tax_id |
| customer_sources | One departmental observation / record_id | source, observed master attributes; no truth entity ID |
| products | One operational SKU / product_id | category_id → categories; supplier_id → suppliers; unit_cost, unit_price |
| product_sources | One departmental product observation / record_id | source, sku, observed name, unit, prices |
| suppliers | One operational supplier / supplier_id | name, tax_id, email, updated_at |
| supplier_sources | One departmental supplier observation / record_id | source, observed attributes |
| categories | One category / category_id | category |
| orders | One order / order_id | customer_id → customers; order_date, fulfilled/cancelled |
| order_lines | One order line / line_id | order_id → orders; product_id → products; quantity, discount, historical unit_price/unit_cost, net_amount |
| sales | One invoice per fulfilled order / sale_id | order_id → orders; sale_date, amount; cancelled orders have no invoice |
| inventory | One product at Main warehouse / inventory_id | product_id; opening_qty, received_qty, shipped_qty, on_hand, as_of |
| stock_movements | One signed stock movement / movement_id | product_id; opening/receipt/dispatch, movement_date, quantity |
| evaluation_only/*.csv | Mapping record_id → hidden entity_id | Experiment ground truth; never included in matching features |

## Reproducibility

`numpy.random.default_rng(seed)` controls all stochastic choices. Demo: 120 customers, 48 products, 1,400 orders. Large: 1,800 customers, 360 products, 24,000 orders. Each order has 1–5 lines. Twelve suppliers and four categories appear in both sizes. Every master has two source observations plus an extra copy for every tenth entity. Rows are shuffled deterministically.

Demand is heavy-tailed; 10% of customers are structurally inactive, preferred categories influence product choice, November/December quantities increase, and prices grow gradually by up to 12% across two years. Every 200th sampled line on average has a legitimate bulk quantity. These are constructed patterns, not discoveries about the world. Inventory starts at 100 units per product; all receipts are front-loaded so dispatches never create negative historical inventory. This deliberately simple stock policy is not an inventory optimization model.

Source defects follow index-based rules, documented in `ingestion/synthetic.py`: every fourth second-source name has a missing letter; every fifth second-source email is absent; every nineteenth is malformed; every seventh tax key is absent; every twenty-ninth may conflict with the preceding entity's key; every sixth region is absent; every tenth update is stale. Every eleventh second-source product has a negative observed price. Case, whitespace and phone formats differ by department. Normalization repairs formats and quarantines invalid emails as missing, with a cell audit; it does not silently infer identities or repair conflict values.

Sales are summed from rounded line net amounts. Gross margin uses historical simulated line costs. Stock balances reconcile to signed movements. Structural foreign-key checks run independently of format/domain quality checks.

## Import scope

The explorer accepts arbitrary UTF-8 CSVs for EDA, quality and exported reports. Master CSVs with unique `record_id` plus `name` can use Entity Resolution. Business Intelligence and RFM require the relational bundle contract, so arbitrary uploaded CSVs do not silently replace operational tables. The Python bundle loader accepts folders of the documented CSVs plus a manifest, allowing external relational data to use the same analytics APIs.
