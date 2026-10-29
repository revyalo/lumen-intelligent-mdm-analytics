SELECT p.product_id, p.name, c.category,
       coalesce(sum(f.quantity), 0) AS units,
       coalesce(sum(f.net_amount), 0) AS revenue,
       coalesce(sum(f.net_amount-f.quantity*f.unit_cost), 0) AS gross_margin,
       count(DISTINCT f.order_id) AS orders
FROM products p JOIN categories c USING (category_id)
LEFT JOIN fulfilled_lines f ON f.product_id = p.product_id
GROUP BY p.product_id, p.name, c.category
ORDER BY revenue DESC, p.product_id
