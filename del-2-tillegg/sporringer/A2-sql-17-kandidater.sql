-- A2/17 Eksempelselskaper for kontroll mot den levende kilden (2024-åpninger)
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud,
         (SELECT max(i.fristdag) FROM kunngjoring.insolvens i
            WHERE i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning') AS fristdag,
         (SELECT max(k.kid) FROM kunngjoring.kunngjoring k WHERE k.orgnr=o.orgnr) AS kid,
         row_number() OVER (PARTITION BY EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter')
                 ORDER BY o.opened DESC, o.orgnr) AS rn
  FROM o)
SELECT oppbud, orgnr, opened, fristdag, (opened-fristdag) AS gap, kid
FROM b WHERE rn <= 3 ORDER BY oppbud DESC, opened DESC;
