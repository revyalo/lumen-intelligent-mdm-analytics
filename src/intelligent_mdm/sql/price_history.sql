SELECT date_trunc('month', f.order_date) AS month, c.category,
       sum(f.quantity*f.unit_price)/nullif(sum(f.quantity),0) AS weighted_unit_price,
       sum(f.quantity) AS units
FROM fulfilled_lines f JOIN products p USING (product_id) JOIN categories c USING (category_id)
GROUP BY 1, 2 ORDER BY 1, 2
