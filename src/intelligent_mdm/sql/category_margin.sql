SELECT c.category,
       sum(f.net_amount) AS revenue,
       sum(f.net_amount-f.quantity*f.unit_cost) AS gross_margin,
       100*sum(f.net_amount-f.quantity*f.unit_cost)/nullif(sum(f.net_amount),0) AS margin_pct
FROM fulfilled_lines f
JOIN products p USING (product_id) JOIN categories c USING (category_id)
GROUP BY c.category ORDER BY gross_margin DESC
