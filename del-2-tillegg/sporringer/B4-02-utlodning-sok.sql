-- B4-02: exhaustive corpus-wide search for ANY dividend / payout / coverage information.
-- Four surfaces: felt.felt (key), felt.verdi (value), kunngjoring.type_kanon (canonical type),
-- kunngjoring.type (raw 80-char-truncated headline), v_hendelse.detalj (the tail cut off the type).
\timing off

-- (a) felt KEYS matching payout vocabulary
SELECT 'a_felt_nokkel_treff' AS hva, f.felt, count(*) AS rader, count(DISTINCT f.orgnr) AS selskaper
FROM kunngjoring.felt f
WHERE f.felt ~* '(utlodn|dividend|utbetal|utbytte|dekningsprosent|massekrav|prioritert|lønnsgaranti|lonnsgaranti|fordringshaver|anmeldt)'
GROUP BY 2 ORDER BY 3 DESC;

-- (b) felt VALUES matching payout vocabulary -- one full pass, counters per pattern
SELECT 'b_felt_verdi_treff' AS hva,
  count(*) FILTER (WHERE f.verdi ~* 'utlodn')            AS utlodning,
  count(*) FILTER (WHERE f.verdi ~* 'dividend')          AS dividende,
  count(*) FILTER (WHERE f.verdi ~* 'utbetal')           AS utbetaling,
  count(*) FILTER (WHERE f.verdi ~* 'utbytte')           AS utbytte,
  count(*) FILTER (WHERE f.verdi ~* 'dekningsprosent')   AS dekningsprosent,
  count(*) FILTER (WHERE f.verdi ~* 'massekrav')         AS massekrav,
  count(*) FILTER (WHERE f.verdi ~* '(u?prioritert)')    AS prioritert,
  count(*) FILTER (WHERE f.verdi ~* '(lønnsgaranti|lonnsgaranti)') AS lonnsgaranti,
  count(*) FILTER (WHERE f.verdi ~* 'fordringshaver')    AS fordringshaver,
  count(*) FILTER (WHERE f.verdi ~* 'boets midler')      AS boets_midler,
  count(*) AS rader_totalt
FROM kunngjoring.felt f;

-- (c) which (felt, value) pairs actually matched, if any
SELECT 'c_felt_verdi_eksempler' AS hva, f.felt, left(f.verdi,140) AS verdi, count(*) AS rader, count(DISTINCT f.orgnr) AS selskaper
FROM kunngjoring.felt f
WHERE f.verdi ~* '(utlodn|dividend|dekningsprosent|massekrav|lønnsgaranti|lonnsgaranti)'
GROUP BY 2,3 ORDER BY 4 DESC LIMIT 60;

-- (d) canonical announcement types matching payout vocabulary (144-type universe)
SELECT 'd_type_kanon_treff' AS hva, k.type_kanon, count(*) AS rader, count(DISTINCT k.orgnr) AS selskaper, min(k.dato) AS forste, max(k.dato) AS siste
FROM kunngjoring.kunngjoring k
WHERE k.type_kanon ~* '(utlodn|dividend|utbetal|utbytte|dekningsprosent|massekrav|lønnsgaranti|lonnsgaranti|oppheving|opphev|fortsettelse|gjenoppta)'
GROUP BY 2 ORDER BY 3 DESC;

-- (e) raw (80-char truncated) type strings matching payout vocabulary
SELECT 'e_type_raa_treff' AS hva, left(k.type,80) AS type_raa, count(*) AS rader, count(DISTINCT k.orgnr) AS selskaper
FROM kunngjoring.kunngjoring k
WHERE k.type ~* '(utlodn|dividend|dekningsprosent|massekrav|lønnsgaranti|lonnsgaranti)'
GROUP BY 2 ORDER BY 3 DESC LIMIT 60;

-- (f) v_hendelse.detalj (the tail the canonicaliser cut off)
SELECT 'f_detalj_treff' AS hva, left(h.detalj,120) AS detalj, h.type_kanon, count(*) AS rader, count(DISTINCT h.orgnr) AS selskaper
FROM kunngjoring.v_hendelse h
WHERE h.detalj ~* '(utlodn|dividend|dekningsprosent|massekrav|lønnsgaranti|lonnsgaranti)'
GROUP BY 2,3 ORDER BY 4 DESC LIMIT 60;

-- (g) how many detalj values are non-empty at all, so we know how big that surface is
SELECT 'g_detalj_dekning' AS hva, count(*) AS rader_total, count(*) FILTER (WHERE coalesce(trim(h.detalj),'')<>'') AS rader_med_detalj,
       count(DISTINCT h.orgnr) FILTER (WHERE coalesce(trim(h.detalj),'')<>'') AS selskaper_med_detalj
FROM kunngjoring.v_hendelse h;
