-- A2/01 Hva er "Åpnet etter" i korpuset: verdier, typer, år
\echo == verdier ==
select verdi, count(*) from kunngjoring.felt where felt='Åpnet etter' group by 1 order by 2 desc;
\echo == kunngj_type ==
select kunngj_type, count(*) from kunngjoring.felt where felt='Åpnet etter' group by 1 order by 2 desc limit 20;
\echo == aar ==
select extract(year from dato)::int as aar, count(*) from kunngjoring.felt where felt='Åpnet etter' group by 1 order by 1;
\echo == like-varianter av feltnavnet ==
select felt, count(*) from kunngjoring.felt where felt ilike '%pnet%' or felt ilike '%oppbud%' or felt ilike '%begj%' group by 1 order by 2 desc limit 30;
