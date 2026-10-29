-- HAVING: repeated purchasing is based on orders, not the number of order lines.
SELECT customer_id, count(DISTINCT order_id) AS orders, sum(net_amount) AS revenue
FROM fulfilled_lines
GROUP BY customer_id HAVING count(DISTINCT order_id) >= 3
ORDER BY revenue DESC
