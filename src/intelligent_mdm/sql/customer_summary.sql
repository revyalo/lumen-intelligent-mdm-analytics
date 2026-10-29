-- Multiple JOINs, distinct transaction counts, all customers including non-buyers.
SELECT c.customer_id, c.name, c.region,
       count(DISTINCT f.order_id) AS frequency,
       coalesce(sum(f.net_amount), 0) AS revenue,
       max(f.order_date) AS last_purchase,
       coalesce(sum(f.net_amount) / nullif(count(DISTINCT f.order_id), 0), 0) AS average_order
FROM customers c
LEFT JOIN fulfilled_lines f ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.name, c.region
ORDER BY revenue DESC, c.customer_id
