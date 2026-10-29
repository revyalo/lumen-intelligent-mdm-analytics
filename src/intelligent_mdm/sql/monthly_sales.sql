-- CTE + temporal aggregation + window function. Zero-sales months are included.
WITH calendar AS (
 SELECT unnest(generate_series(date_trunc('month', min(order_date)),
                               date_trunc('month', max(order_date)), interval '1 month')) AS month
 FROM orders
), monthly AS (
 SELECT date_trunc('month', sale_date) AS month, sum(amount) AS revenue,
        count(DISTINCT order_id) AS orders
 FROM sales GROUP BY 1
), filled AS (
 SELECT c.month, coalesce(m.revenue, 0) AS revenue, coalesce(m.orders, 0) AS orders
 FROM calendar c LEFT JOIN monthly m USING (month)
), prior AS (
 SELECT *, lag(revenue) OVER (ORDER BY month) AS previous_revenue FROM filled
)
SELECT *, 100 * (revenue-previous_revenue) / nullif(previous_revenue, 0) AS mom_pct
FROM prior ORDER BY month
