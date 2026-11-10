-- D2-01-revisor-ved-apning.sql — lane D2 (sjekklisten kjørt på nytt med «revisor registrert ved åpningen»), 12.09.2026.
-- KUN SELECT/WITH. Utdata: D2-01-revisor-ved-apning.csv
--
-- Radnivå-dump av alle «Revisor»-felt på kohortens kunngjøringer datert TIL OG MED åpningsdagen. Tilstanden ved åpningen
-- avledes i D2-sjekkliste.py (siste felt strengt før åpningen = hovedvariant, identisk med V-B2-04; siste felt t.o.m. åpningsdagen = sensitivitet).
-- Revisornavnet (verdi) lagres ikke — bare klassen: 'utgaar' (verdi begynner med «Utgår» = revisor strøket/fravalgt), 'tom', ellers 'navngitt'.
-- Bærere av feltet i kohorten (probe 12.09.2026): «Endring av revisor» (1 658 bo navngitt / 739 Utgår), «Nyregistrering» (956 navngitt), rettelser (6).
-- Korpuset for kunngjoring.felt går fra 1999-11-02; ingen bo i gruppen uten Revisor-felt er stiftet før 2011-06-23 (revisjonsfritaket for små AS kom 1. mai 2011).
WITH o AS (
  SELECT orgnr, min(dato) AS opened
  FROM kunngjoring.insolvens
  WHERE type = 'Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31'
  GROUP BY 1)
SELECT o.orgnr, o.opened, f.dato, f.kunngj_type,
       CASE WHEN f.verdi ILIKE 'Utgår%' THEN 'utgaar'
            WHEN btrim(coalesce(f.verdi, '')) = '' THEN 'tom'
            ELSE 'navngitt' END AS klasse
FROM kunngjoring.felt f
JOIN o USING (orgnr)
WHERE f.felt = 'Revisor' AND f.dato <= o.opened
ORDER BY o.orgnr, f.dato, f.kunngj_type;
