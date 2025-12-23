-- Lens, Count, %
SELECT
    lens_name,
    COUNT(*) AS shot_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    ) AS shot_pct
FROM photos
GROUP BY lens_name
ORDER BY shot_count DESC;


--

