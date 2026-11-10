-- V-B3: independent re-check of the «Åpnet etter» field semantics on the cohort's opening announcements. READ-ONLY.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'apnet_etter_verdier' AS hva, f.verdi, count(*) AS n, count(DISTINCT f.orgnr) AS selskaper
FROM o JOIN kunngjoring.felt f ON f.orgnr=o.orgnr AND f.dato=o.opened AND f.kunngj_type='Konkurs - åpning'
WHERE f.felt='Åpnet etter' GROUP BY 2 ORDER BY 3 DESC;
-- any opening announcement with NO felt rows at all (a parser miss would look like "not oppbud")
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'felt_dekning' AS hva,
       count(*) AS bo,
       count(*) FILTER (WHERE nf=0) AS uten_noen_felt,
       count(*) FILTER (WHERE nf>0 AND NOT opp) AS med_felt_men_uten_apnet_etter,
       count(*) FILTER (WHERE opp) AS med_apnet_etter
FROM (SELECT o.orgnr,
             (SELECT count(*) FROM kunngjoring.felt f WHERE f.orgnr=o.orgnr AND f.dato=o.opened AND f.kunngj_type='Konkurs - åpning') AS nf,
             EXISTS (SELECT 1 FROM kunngjoring.felt f WHERE f.orgnr=o.orgnr AND f.dato=o.opened AND f.kunngj_type='Konkurs - åpning' AND f.felt='Åpnet etter') AS opp
      FROM o) t;
-- felt-key inventory on the opening announcements, to see what distinguishes the two groups
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
op AS (SELECT o.orgnr, o.opened,
              EXISTS (SELECT 1 FROM kunngjoring.felt f WHERE f.orgnr=o.orgnr AND f.dato=o.opened AND f.kunngj_type='Konkurs - åpning' AND f.felt='Åpnet etter') AS opp
       FROM o)
SELECT 'feltnokler' AS hva, f.felt, count(*) FILTER (WHERE op.opp) AS i_oppbud, count(*) FILTER (WHERE NOT op.opp) AS i_begjaering
FROM op JOIN kunngjoring.felt f ON f.orgnr=op.orgnr AND f.dato=op.opened AND f.kunngj_type='Konkurs - åpning'
GROUP BY 2 ORDER BY 3+4 DESC LIMIT 25;
