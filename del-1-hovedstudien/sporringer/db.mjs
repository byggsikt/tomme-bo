// Tilkobling til PostgreSQL for studiens skript. Ingen hemmeligheter her:
// alt leses fra miljøvariabler, eller fra en .env-fil i depotets rot.
//
//   INTEL_DATABASE_URL=postgres://bruker:passord@vert:5432/database
// eller
//   INTEL_PG_HOST, INTEL_PG_PORT, INTEL_PG_USER, INTEL_PG_PASSWORD, INTEL_PG_DB

import { readFile } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";

const { Pool } = pg;

const here = path.dirname(fileURLToPath(import.meta.url));
export const repoRoot = path.resolve(here, "..", "..");

const DEFAULTS = {
  INTEL_PG_HOST: "127.0.0.1",
  INTEL_PG_PORT: "5432",
  INTEL_PG_USER: "postgres",
  INTEL_PG_DB: "tomme_bo",
};

let envLoaded = false;

function parseEnvFile(contents) {
  const out = {};
  for (const rawLine of contents.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (key) out[key] = value;
  }
  return out;
}

export function loadIntelEnv() {
  if (envLoaded) return;
  for (const file of [".env.local", ".env"]) {
    const full = path.join(repoRoot, file);
    if (!existsSync(full)) continue;
    const parsed = parseEnvFile(readFileSync(full, "utf8"));
    for (const [key, value] of Object.entries(parsed)) {
      if (process.env[key] === undefined) process.env[key] = value;
    }
  }
  envLoaded = true;
}

export function getDbConfig() {
  loadIntelEnv();
  const url = process.env.INTEL_DATABASE_URL;
  if (url) return { connectionString: url };
  const get = (k) => process.env[k] ?? DEFAULTS[k];
  return {
    host: get("INTEL_PG_HOST"),
    port: Number(get("INTEL_PG_PORT")),
    user: get("INTEL_PG_USER"),
    password: process.env.INTEL_PG_PASSWORD,
    database: get("INTEL_PG_DB"),
  };
}

let pool;

export function getPool() {
  if (!pool) {
    pool = new Pool({ ...getDbConfig(), max: 8, idleTimeoutMillis: 10_000 });
  }
  return pool;
}

export async function query(text, params = []) {
  return getPool().query(text, params);
}

export async function withClient(fn) {
  const client = await getPool().connect();
  try {
    return await fn(client);
  } finally {
    client.release();
  }
}

export async function runSqlFile(absPath) {
  const sql = await readFile(absPath, "utf8");
  return getPool().query(sql);
}

export async function closePool() {
  if (pool) {
    await pool.end();
    pool = undefined;
  }
}
