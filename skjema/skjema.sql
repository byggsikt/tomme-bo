-- ============================================================================
--  skjema.sql — tabellkontrakten for «Tomme bo»
--
--  Kjør denne i en tom PostgreSQL-database (versjon 14 eller nyere). Fyll så
--  tabellene fra kunngjøringene og registerdataene du selv henter fra
--  Brønnøysundregistrene (kolonne for kolonne beskrevet i SKJEMA.md), og kjør
--  studiens skript uendret. Tabell- og kolonnenavnene er de skriptene bruker.
-- ============================================================================

create schema if not exists kunngjoring;
create schema if not exists company_intel;

-- ---------------------------------------------------------------------------
-- 1. Kanonisk kunngjøringstype
--    På kunngjøringssiden står overskrift og brødtekst i samme tekststreng,
--    uten skilletegn. kanoniser_type klipper strengen ved skjøten og gir den
--    korte, stabile typen («Konkurs - åpning», «Sletting», …). type_detalj
--    gir resten av strengen, slik at ingenting går tapt.
-- ---------------------------------------------------------------------------
create or replace function kunngjoring.kanoniser_type(raa text)
returns text language sql immutable as $$
  with s0 as (select coalesce(trim(raa),'') as t),
       s1 as (select coalesce(substring(t from '^(.*?[a-zæøå])[A-ZÆØÅ]'), t) as t from s0),
       s2 as (select case when length(t) > 40
                     then coalesce(substring(t from '^(.*?[A-ZÆØÅ])[A-ZÆØÅ][a-zæøå]'), t)
                     else t end as t from s1),
       s3 as (select regexp_replace(
                       regexp_replace(
                         regexp_replace(t, '\s+er:\s.*$', ''),
                       '\s+(til|fra)\s+\d{1,2}\.\d{1,2}\.\d{4}.*$',''),
                     '\s+\d{1,2}\.\d{1,2}\.\d{4}.*$','') as t from s2),
       s4 as (select case when t = upper(t) and t ~ '[A-ZÆØÅ]{4,}'
                     then upper(left(t,1)) || lower(substring(t from 2))
                     else t end as t from s3)
  select nullif(trim(t),'') from s4;
$$;

create or replace function kunngjoring.type_detalj(raa text)
returns text language sql immutable as $$
  select nullif(trim(substring(coalesce(raa,'')
         from length(coalesce(kunngjoring.kanoniser_type(raa),''))+1)),'');
$$;

-- ---------------------------------------------------------------------------
-- 2. Alle kunngjøringer: én rad per kunngjøring per foretak
-- ---------------------------------------------------------------------------
create table if not exists kunngjoring.kunngjoring (
  orgnr      char(9) not null,
  kid        bigint,                                  -- kunngjøringens id hos Brønnøysundregistrene
  dato       date    not null,                        -- kunngjøringsdato
  type       text,                                    -- overskriften slik den står på kunngjøringssiden
  register   text,                                    -- Foretaksregisteret | Regnskapsregisteret | Konkursregisteret | tom
  type_kanon text generated always as (kunngjoring.kanoniser_type(type)) stored
);
create index if not exists ix_kunngj_kanon_dato on kunngjoring.kunngjoring (type_kanon, dato desc);
create index if not exists ix_kunngj_org_kanon  on kunngjoring.kunngjoring (orgnr, type_kanon);

-- ---------------------------------------------------------------------------
-- 3. Hva en kanonisk type betyr
--    kategori          semantisk gruppe
--    er_livslopslutt   avslutter kunngjøringen foretakets liv?
--    er_insolvensspor  er den del av et insolvensløp?
--    utfall            hvilket utfall den beviser (NULL hvis ingen)
--    Fylles fra typene som finnes i kunngjoring.kunngjoring. Idempotent.
-- ---------------------------------------------------------------------------
create table if not exists kunngjoring.hendelsestype (
  type_kanon        text primary key,
  kategori          text not null,
  er_livslopslutt   boolean not null default false,
  er_insolvensspor  boolean not null default false,
  utfall            text,
  beskrivelse       text
);

insert into kunngjoring.hendelsestype (type_kanon, kategori, er_livslopslutt, er_insolvensspor, utfall)
select k, kat, slutt, insolv, utf from (
  select distinct type_kanon as k,
    case
      when type_kanon in ('Nyregistrering','Reinnføring i Foretaksregisteret')      then 'stiftelse'
      when type_kanon ~ '^Endring av (styre|daglig leder|signatur|revisor)'          then 'styre_ledelse'
      when type_kanon ~ '^Endring av (foretaksnavn|firma|forretningsadresse|formål|vedtektsdato)'
                                                                                     then 'identitet'
      when type_kanon ~ '^(Endring av kapital|Fullmakt|Nedsettelse av|Konvertibelt|Frittstående tegningsretter|Tegningsrettsaksjer|Utdeling av)'
                                                                                     then 'kapital'
      when type_kanon ~ '^(Godkjent årsregnskap|Godkjent mellombalanse|Revisjon av årsregnskap)'
                                                                                     then 'regnskap'
      when type_kanon ~ '^(Kreditorvarsel|Retting av [Kk]reditorvarsel|Korrigering av kreditorvarsel)'
                                                                                     then 'kreditorvarsel'
      when type_kanon ~ '^(Fusjonsplan|Fisjonsplan|Gjennomføring av (fusjon|fisjon)|Omgjøring|Delvis omgjøring|Omdanningsplan|Fisjon$|Fusjon)'
                                                                                     then 'omorganisering'
      when type_kanon = 'Varsel om tvangsoppløsning'                                 then 'doedsvarsel'
      when type_kanon ~ '^(Konkurs|Tvangsoppløsning|Tvangsavvikling|Skiftesamling|Ny skiftesamling|Første skiftesamling|Kontaktinformasjon til ny bostyrer|Ny fordringsfrist|Fordringshavermøte|Fortsettelse av bobehandling|Gjelder konkurs|Gjelder rekonstruksjon|E-postadresse til rekonstruktør)'
                                                                                     then 'insolvens'
      when type_kanon ~ '^(Sletting|Oppløsning)'                                     then 'avvikling'
      when type_kanon ~ '^(Rettelse|Retting av)'                                     then 'rettelse'
      else 'annet'
    end as kat,
    (type_kanon in ('Sletting','Sletting etter fusjon','Sletting etter fisjon'))      as slutt,
    (type_kanon ~ '^(Konkurs|Tvangsoppløsning|Tvangsavvikling|Varsel om tvangsoppløsning|Skiftesamling|Ny skiftesamling|Første skiftesamling|Kontaktinformasjon til ny bostyrer|Ny fordringsfrist|Fordringshavermøte|Fortsettelse av bobehandling)')
                                                                                     as insolv,
    case
      when type_kanon = 'Konkurs - åpning'          then 'konkurs'
      when type_kanon ~ '^Tvangsoppløsning'         then 'tvangsopplosning'
      when type_kanon ~ '^Tvangsavvikling'          then 'tvangsavvikling'
      when type_kanon = 'Varsel om tvangsoppløsning' then 'varslet_tvang'
      when type_kanon = 'Sletting etter fusjon'     then 'oppslukt_fusjon'
      when type_kanon = 'Sletting etter fisjon'     then 'delt_fisjon'
      when type_kanon = 'Sletting'                  then 'slettet_uten_oppgitt_grunn'
      else null
    end as utf
  from kunngjoring.kunngjoring
  where type_kanon is not null
) s
on conflict (type_kanon) do nothing;

-- ---------------------------------------------------------------------------
-- 4. Den semantiske tidslinjen: én rad per kunngjøring, ferdig merket
-- ---------------------------------------------------------------------------
create or replace view kunngjoring.v_hendelse as
select k.orgnr, k.dato, k.kid, k.register,
       k.type_kanon,
       kunngjoring.type_detalj(k.type) as detalj,
       h.kategori, h.er_livslopslutt, h.er_insolvensspor, h.utfall,
       k.type as type_raa
from kunngjoring.kunngjoring k
left join kunngjoring.hendelsestype h using (type_kanon);

create or replace view kunngjoring.v_insolvensloep as
select orgnr,
       min(dato) filter (where type_kanon='Varsel om tvangsoppløsning')      as forste_varsel,
       max(dato) filter (where type_kanon='Varsel om tvangsoppløsning')      as siste_varsel,
       count(*) filter (where type_kanon='Varsel om tvangsoppløsning')       as antall_varsel,
       min(dato) filter (where type_kanon='Konkurs - åpning')                as konkurs_apnet,
       min(dato) filter (where type_kanon like 'Tvangs%')                    as tvang_dato,
       min(dato) filter (where er_livslopslutt)                              as slettet,
       max(utfall) filter (where er_livslopslutt)                            as sluttutfall
from kunngjoring.v_hendelse
where er_insolvensspor or er_livslopslutt
group by orgnr;

-- ---------------------------------------------------------------------------
-- 5. Insolvens- og avviklingskunngjøringene med feltene fra kunngjøringssiden
--    Én rad per kunngjøring av typene i SKJEMA.md § 3.
-- ---------------------------------------------------------------------------
create table if not exists kunngjoring.insolvens (
  orgnr     char(9) not null,
  dato      date    not null,     -- kunngjøringsdato
  type      text    not null,     -- kanonisk type, f.eks. 'Konkurs - åpning'
  tingrett  text,                 -- tingretten slik den er trykt
  bostyrer  text,                 -- bostyrer slik det er trykt (studien bruker bare «utfylt / ikke utfylt»)
  saksnr    text,                 -- rettens saksnummer
  fristdag  date,                 -- fristdagen etter dekningsloven
  bransje   text,                 -- den trykte næringsangivelsen («Bransje/stilling»)
  kapital   text                  -- kapitalangivelsen slik den er trykt
);
create index if not exists ix_insolvens_org  on kunngjoring.insolvens (orgnr, dato);
create index if not exists ix_insolvens_type on kunngjoring.insolvens (type, dato);

-- ---------------------------------------------------------------------------
-- 6. Alle navngitte felt på kunngjøringssidene, som nøkkel og verdi
-- ---------------------------------------------------------------------------
create table if not exists kunngjoring.felt (
  orgnr       char(9) not null,
  dato        date    not null,   -- kunngjøringsdato
  kunngj_type text,               -- kanonisk type for kunngjøringen feltet står i
  felt        text    not null,   -- feltets etikett, f.eks. 'Åpnet etter', 'Revisor', 'Daglig leder'
  verdi       text                -- feltets verdi slik den er trykt
);
create index if not exists ix_felt_org  on kunngjoring.felt (orgnr, dato);
create index if not exists ix_felt_felt on kunngjoring.felt (felt);

-- ---------------------------------------------------------------------------
-- 7. Én rad per foretak, avledet av foretakets kunngjøringer
-- ---------------------------------------------------------------------------
create table if not exists kunngjoring.selskap (
  orgnr            char(9) primary key,
  navn_gjeldende   text,
  antall_kunngj    integer,
  forste_kunngj    date,
  siste_kunngj     date,
  stiftet          date,          -- dato for «Nyregistrering»
  slettet          date,          -- dato for første «Sletting …»
  konkurs_dato     date,          -- dato for første «Konkurs - åpning»
  tvangs_dato      date,          -- dato for første «Tvangsoppløsning …» / «Tvangsavvikling …»
  kapital_ved_reg  numeric,       -- kapital i «Nyregistrering»
  kapital_siste    numeric,       -- siste kunngjorte kapital
  organisasjonsform text,         -- 'AS', 'ASA', …
  formaal_siste    text
);

create table if not exists kunngjoring.adresse (
  orgnr       char(9) not null,
  dato        date    not null,
  kilde       text,               -- hvilken kunngjøring adressen står i
  gate        text,
  postnr      char(4),
  sted        text,
  kommune     text,
  navn_da     text,               -- foretaksnavnet på kunngjøringstidspunktet
  kunngj_type text
);

create table if not exists kunngjoring.kapital (
  orgnr       char(9) not null,
  dato        date    not null,
  kunngj_type text,
  belop       numeric,            -- beløpet i feltet «Kapital»
  valuta      char(3),
  raa         text                -- feltet slik det er trykt
);

-- ---------------------------------------------------------------------------
-- 8. Enhetsregisteret (åpent API): én rad per foretak
-- ---------------------------------------------------------------------------
create table if not exists company_intel.company (
  orgnr                              text primary key,
  name                               text,
  normalized_name                    text,
  org_form_code                      text,            -- organisasjonsform.kode
  org_form_text                      text,
  registered_enhetsregisteret_at     date,
  registered_foretaksregisteret_at   date,
  is_under_bankruptcy                boolean,
  is_under_liquidation               boolean,
  is_deleted                         boolean,         -- slettedato finnes
  deleted_at                         date,            -- slettedato
  last_submitted_accounts_year       integer,         -- sisteInnsendteAarsregnskap
  employee_count                     integer,
  industry_code_1                    text,            -- naeringskode1.kode
  industry_text_1                    text,            -- naeringskode1.beskrivelse
  industry_code_2                    text,
  industry_text_2                    text,
  industry_code_3                    text,
  industry_text_3                    text,
  municipality_number                text,
  municipality_name                  text
);

create table if not exists company_intel.brreg_ansatte (
  orgnr           text primary key,
  antall_ansatte  integer,        -- antallAnsatte
  har_registrert  boolean         -- harRegistrertAntallAnsatte
);

-- ---------------------------------------------------------------------------
-- 9. Regnskapsregisteret (åpent API): én rad per foretak og regnskapsår, hele kroner
-- ---------------------------------------------------------------------------
create table if not exists company_intel.annual_account (
  id                    uuid primary key default gen_random_uuid(),
  orgnr                 text    not null,
  fiscal_year           integer not null,          -- året i regnskapsperiode.tilDato
  period_label          text,
  source_name           text,                      -- 'brreg_regnskapsregister'
  currency              text,                      -- 'NOK'
  amount_unit           text,                      -- 'NOK' (hele kroner)
  operating_revenue     numeric,                   -- sumDriftsinntekter
  operating_result      numeric,                   -- driftsresultat
  result_before_tax     numeric,                   -- ordinaertResultatFoerSkattekostnad
  annual_result         numeric,                   -- aarsresultat
  ebitda                numeric,
  total_assets          numeric,                   -- sumEiendeler
  equity                numeric,                   -- sumEgenkapital
  liabilities           numeric,                   -- sumGjeld
  current_assets        numeric,                   -- sumOmloepsmidler
  current_liabilities   numeric,                   -- sumKortsiktigGjeld
  payroll_expenses      numeric,                   -- loennskostnad
  employee_count        integer,
  checked_at            timestamptz
);
create index if not exists ix_aa_org_year on company_intel.annual_account (orgnr, fiscal_year);

-- ---------------------------------------------------------------------------
-- 10. Kart fra næringsetikett til kategori. Brukes bare av én rekonstruksjons-
--     runde (kohort-06-rekon6.mjs); innholdet tilsvarer bransjekart-v3 i
--     del-1-hovedstudien/data/. Kan stå tom.
-- ---------------------------------------------------------------------------
create table if not exists company_intel.construction_trade_mapping (
  id                uuid primary key default gen_random_uuid(),
  source_orgnr      text,
  source_type       text,
  industry_code     text,
  industry_text     text,
  byggsikt_category text,
  trade_group       text,
  relevance_weight  numeric,
  mapping_reason    text
);
