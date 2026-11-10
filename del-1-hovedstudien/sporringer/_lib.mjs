// Felles hjelpefunksjoner for lane «bransje» (Tomme bo).
// READ-ONLY. Kun SELECT. Ingen skriving mot databasen.
import { getPool, closePool } from "./db.mjs";
import { createHash } from "node:crypto";
import { writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";

export const ROOT = "./del-1-hovedstudien";
export const RUN_DATE = "2026-08-30";

// Kohortvinduer (jf. BRIEF.md §3)
export const COHORT_START = "2023-09-01"; // hovedvindu (overskriftstall)
export const COHORT_END = "2024-12-31";
export const MATURE_START = "2023-08-24"; // «moden kohort» = første innstillingsdato i korpuset
export const CORPUS_END = "2026-08-24";

let pool = null;

export function pg() {
  if (!pool) pool = getPool();
  return pool;
}

/** Kjør SELECT med høy statement_timeout. Kaster hvis SQL ikke er ren lesing. */
export async function q(sql, params = []) {
  const forbidden = /\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|refresh|vacuum|copy)\b/i;
  // tillat ordet «create» kun som del av «CREATE ... » — vi forbyr alt uansett
  if (forbidden.test(sql)) throw new Error("SQL avvist: inneholder ikke-lesende nøkkelord");
  const client = await pg().connect();
  try {
    await client.query("set statement_timeout = '900s'");
    await client.query("set transaction read only", []).catch(() => {});
    const r = await client.query(sql, params);
    return r;
  } finally {
    client.release();
  }
}

export async function done() {
  await closePool();
  pool = null;
}

export function sha256(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

/** Skriv CSV til data/ eller figurer/ og returner {path, sha256, rows}. */
export function writeCsv(relPath, header, rows) {
  const full = path.join(ROOT, relPath).replace(/\\/g, "/");
  mkdirSync(path.dirname(full), { recursive: true });
  const esc = (v) => {
    if (v === null || v === undefined) return "";
    const s = String(v);
    return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const body = [header.join(","), ...rows.map((r) => r.map(esc).join(","))].join("\n") + "\n";
  writeFileSync(full, body, "utf8");
  return { path: full, sha256: sha256(Buffer.from(body, "utf8")), rows: rows.length };
}

export function writeJson(relPath, obj) {
  const full = path.join(ROOT, relPath).replace(/\\/g, "/");
  mkdirSync(path.dirname(full), { recursive: true });
  const body = JSON.stringify(obj, null, 2) + "\n";
  writeFileSync(full, body, "utf8");
  return { path: full, sha256: sha256(Buffer.from(body, "utf8")) };
}

// ---- Clopper–Pearson eksakt binomisk konfidensintervall ------------------
// Bruker relasjonen mellom beta-fordelingen og den inverse regulariserte
// ufullstendige beta-funksjonen. Ren JS, ingen avhengigheter.

function logGamma(z) {
  const g = 7;
  const c = [
    0.99999999999980993, 676.5203681218851, -1259.1392167224028,
    771.32342877765313, -176.61502916214059, 12.507343278686905,
    -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7,
  ];
  if (z < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * z)) - logGamma(1 - z);
  z -= 1;
  let x = c[0];
  for (let i = 1; i < g + 2; i++) x += c[i] / (z + i);
  const t = z + g + 0.5;
  return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x);
}

function betacf(a, b, x) {
  const MAXIT = 300, EPS = 3e-16, FPMIN = 1e-300;
  const qab = a + b, qap = a + 1, qam = a - 1;
  let c = 1, d = 1 - (qab * x) / qap;
  if (Math.abs(d) < FPMIN) d = FPMIN;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= MAXIT; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; h *= d * c;
    aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    const del = d * c; h *= del;
    if (Math.abs(del - 1) < EPS) break;
  }
  return h;
}

/** Regularisert ufullstendig beta I_x(a,b). */
export function ibeta(x, a, b) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const bt = Math.exp(logGamma(a + b) - logGamma(a) - logGamma(b) + a * Math.log(x) + b * Math.log(1 - x));
  if (x < (a + 1) / (a + b + 2)) return (bt * betacf(a, b, x)) / a;
  return 1 - (bt * betacf(b, a, 1 - x)) / b;
}

/** Invers I_x(a,b) = p ved bisection (robust, tilstrekkelig presis). */
export function ibetaInv(p, a, b) {
  let lo = 0, hi = 1;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (ibeta(mid, a, b) < p) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
}

/**
 * Clopper–Pearson eksakt 95 %-KI for k av n.
 * Nedre = Beta(alpha/2; k, n-k+1), øvre = Beta(1-alpha/2; k+1, n-k).
 */
export function clopperPearson(k, n, alpha = 0.05) {
  if (n === 0) return [null, null];
  const lo = k === 0 ? 0 : ibetaInv(alpha / 2, k, n - k + 1);
  const hi = k === n ? 1 : ibetaInv(1 - alpha / 2, k + 1, n - k);
  return [lo, hi];
}

export const pct = (x, d = 1) => (x === null || x === undefined ? "" : (100 * x).toFixed(d));
