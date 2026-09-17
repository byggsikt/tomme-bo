// LANE 1 / kohort — rekognosering 6 (READ-ONLY): jakt paa SN2007-vokabular.
import { getPool, closePool } from "./db.mjs";
const pool = getPool();
const out = (l, r) => { console.log("\n=== " + l + " ==="); console.log(JSON.stringify(r, null, 1)); };
const probe = async (tabell, kode, tekst) => {
  try {
    out(`${tabell}: har den SN2007-etiketter?`, (await pool.query(`
      select
        (select count(*) from ${tabell} where ${tekst} ilike 'Butikkhandel med kl%') as butikkhandel_klaer_sn2007,
        (select count(*) from ${tabell} where ${tekst} ilike 'Detaljhandel med kl%') as detaljhandel_klaer_sn2025,
        (select count(*) from ${tabell} where ${tekst} ilike 'Blikkenslagerarbeid%') as blikkenslager,
        (select count(*) from ${tabell} where ${tekst} ilike 'Allmenn legetjeneste%') as allmenn_legetj_sn2007,
        (select count(*) from ${tabell} where ${tekst} ilike 'Allmennlegetjenester%') as allmennlegetj_sn2025,
        (select count(distinct ${tekst}) from ${tabell} where ${kode} is not null) as distinkte_etiketter
    `)).rows);
  } catch (e) { console.log(`${tabell}: FEIL ${e.message}`); }
};
try {
  await pool.query("set statement_timeout = '900s'");
  await probe("company_intel.company", "industry_code_1", "industry_text_1");
  await probe("company_intel.company_backup_20260808", "industry_code_1", "industry_text_1");
  await probe("company_intel.subunit", "industry_code_1", "industry_text_1");
  await probe("company_intel.subunit_bulk", "industry_code_1", "industry_text_1");

  out("construction_trade_mapping — hva er det?", (await pool.query(`
    select * from company_intel.construction_trade_mapping order by industry_code limit 60
  `)).rows);
  out("construction_trade_mapping — antall rader", (await pool.query(`
    select count(*) as rader from company_intel.construction_trade_mapping
  `)).rows);
  out("kolonner i construction_trade_mapping", (await pool.query(`
    select column_name, data_type from information_schema.columns
    where table_schema='company_intel' and table_name='construction_trade_mapping' order by ordinal_position
  `)).rows);
} catch (e) { console.error("FEIL:", e.message); } finally { await closePool(); }
