// «Tomme bo» — REVISJON 2 (fagfellevurdering). Felles statistikkbibliotek.
//
// READ-ONLY. Ingen databasetilgang: alle beregninger kjøres på det frosne
// kohortuttrekket data/_kohort-rader-arbeidskopi.json (5 165 foretak, ingen
// orgnr, ingen personer), slik at revisjonens tall er knyttet til nøyaktig
// samme kohort som resten av studien.
//
// Datagrunnlag: offentlig tilgjengelige registerkunngjøringer om
// konkursbehandling. Sensureringsdato (korpusslutt) 2026-08-24.
//
// Alt her er ren JS uten avhengigheter — hver estimator er skrevet ut slik at
// den kan etterprøves linje for linje.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";

export const ROOT = "./del-1-hovedstudien";
export const KJORT = "2026-08-30";
export const KORPUSSLUTT = "2026-08-24";
export const VINDU = ["2023-09-01", "2024-12-31"];

// Horisonter: måneder operasjonalisert som hele dager.
export const H12 = 365, H18 = 548, H24 = 730;

// ---------------------------------------------------------------------------
// 1. Kohort
// ---------------------------------------------------------------------------

const DAG = 86400000;
const dnum = (s) => Date.parse(s + "T00:00:00Z");

/**
 * Leser det frosne kohortuttrekket og bygger konkurrerende-risiko-datasettet.
 *
 * Hendelsesmodell (tre absorberende utfall fra åpningstidspunktet):
 *   arsak 1 = innstilling etter kkl. § 135
 *   arsak 2 = ordinær avslutning av bobehandlingen (konkurrerende hendelse)
 *   arsak 0 = fortsatt uavgjort per korpusslutt (høyresensurert)
 *
 * RANDTILFELLE (3 av 5 165 = 0,058 %): tre foretak bærer i tillegg en eldre
 * innstilling 111–177 dager FØR åpningen (et tidligere konkursløp der åpningen
 * er utgått hos kilden). Talljournalens utfallsregel gjør dem innstilt i DETTE
 * løpet, men det frosne uttrekket bærer bare den eldre datoen. De behandles
 * derfor slik:
 *   randregel = "sensurert"  (PRIMÆR)  — sensurert ved korpusslutt; gir en
 *                                        NEDRE grense for insidensen
 *   randregel = "tidligst"   (GRENSE)  — hendelse på dag 1; gir en ØVRE grense
 * Differansen mellom de to rapporteres eksplisitt overalt der den kan påvirke
 * et publisert tall.
 */
export function lesKohort(randregel = "sensurert") {
  const rå = JSON.parse(readFileSync(`${ROOT}/data/_kohort-rader-arbeidskopi.json`, "utf8"));
  const slutt = dnum(KORPUSSLUTT);
  const rader = rå.map((r) => {
    const oppf = Math.round((slutt - dnum(r.aapning)) / DAG);
    const rand = r.dager_til_innstilling !== null && r.dager_til_innstilling < 0;
    let t, arsak;
    if (rand) {
      // innstilt, men post-åpnings-datoen finnes ikke i det frosne uttrekket
      if (randregel === "tidligst") { t = 1; arsak = 1; }
      else { t = oppf; arsak = 0; }
    } else if (r.innstilling) {
      t = r.dager_til_innstilling; arsak = 1;
    } else if (r.avslutning) {
      t = r.dager_til_avslutning; arsak = 2;
    } else {
      t = oppf; arsak = 0;
    }
    if (t < 0) t = 0;
    return {
      aapning: r.aapning,
      kvartal: r.aapning.slice(0, 4) + "K" + (Math.floor(+r.aapning.slice(5, 7) / 3.0001) + 1),
      tingrett: r.tingrett,
      bransje: (r.bransje || "").split("\n")[0].trim(),
      n2: r.nace ? String(r.nace).slice(0, 2) : "ukjent",
      bygg: r.bygg_utforende === true,
      byggF: r.bygg_F === true,
      utfall: r.utfall,
      innstilt: r.utfall === "innstilt" || r.utfall === "begge",
      oppfolging: oppf,
      randtilfelle: rand,
      t, arsak,
    };
  });
  return rader;
}

// ---------------------------------------------------------------------------
// 2. Grunnleggende fordelinger
// ---------------------------------------------------------------------------

export function logGamma(z) {
  const g = 7;
  const c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028,
    771.32342877765313, -176.61502916214059, 12.507343278686905,
    -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
  if (z < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * z)) - logGamma(1 - z);
  z -= 1;
  let x = c[0];
  for (let i = 1; i < g + 2; i++) x += c[i] / (z + i);
  const t = z + g + 0.5;
  return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x);
}
export const logChoose = (n, k) => logGamma(n + 1) - logGamma(k + 1) - logGamma(n - k + 1);

/** Standard normal kumulativ fordeling (Cody-type erfc, ~1e-16 relativ). */
export function normCdf(x) {
  const z = Math.abs(x) / Math.SQRT2;
  const t = 1 / (1 + 0.5 * z);
  const y = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 +
    t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 +
    t * (1.48851587 + t * (-0.82215223 + t * 0.17087277))))))))); // = erfc(z)
  return x >= 0 ? 1 - 0.5 * y : 0.5 * y;
}
/** Tosidig normal-p. Rapporteres eksakt så langt double rekker; under ~1e-300 = 0. */
export const pTosidigZ = (z) => 2 * (1 - normCdf(Math.abs(z)));

/** Regularisert ufullstendig gamma P(a,x). */
function gammaP(a, x) {
  if (x <= 0) return 0;
  if (x < a + 1) { // rekke
    let ap = a, sum = 1 / a, del = sum;
    for (let n = 0; n < 1000; n++) {
      ap++; del *= x / ap; sum += del;
      if (Math.abs(del) < Math.abs(sum) * 1e-16) break;
    }
    return sum * Math.exp(-x + a * Math.log(x) - logGamma(a));
  }
  // kjedebrøk for Q(a,x)
  const FPMIN = 1e-300;
  let b = x + 1 - a, c = 1 / FPMIN, d = 1 / b, h = d;
  for (let i = 1; i <= 1000; i++) {
    const an = -i * (i - a);
    b += 2; d = an * d + b; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = b + an / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; const del = d * c; h *= del;
    if (Math.abs(del - 1) < 1e-16) break;
  }
  return 1 - Math.exp(-x + a * Math.log(x) - logGamma(a)) * h;
}
/** Øvre hale i khikvadrat med df frihetsgrader. */
export const pKhi = (x2, df) => (x2 <= 0 ? 1 : 1 - gammaP(df / 2, x2 / 2));

function betacf(a, b, x) {
  const MAXIT = 400, EPS = 3e-16, FPMIN = 1e-300;
  const qab = a + b, qap = a + 1, qam = a - 1;
  let c = 1, d = 1 - (qab * x) / qap;
  if (Math.abs(d) < FPMIN) d = FPMIN;
  d = 1 / d; let h = d;
  for (let m = 1; m <= MAXIT; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; h *= d * c;
    aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; const del = d * c; h *= del;
    if (Math.abs(del - 1) < EPS) break;
  }
  return h;
}
export function ibeta(x, a, b) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const bt = Math.exp(logGamma(a + b) - logGamma(a) - logGamma(b) + a * Math.log(x) + b * Math.log(1 - x));
  return x < (a + 1) / (a + b + 2) ? (bt * betacf(a, b, x)) / a : 1 - (bt * betacf(b, a, 1 - x)) / b;
}
export function ibetaInv(p, a, b) {
  let lo = 0, hi = 1;
  for (let i = 0; i < 200; i++) { const m = (lo + hi) / 2; if (ibeta(m, a, b) < p) lo = m; else hi = m; }
  return (lo + hi) / 2;
}
/** Clopper–Pearson eksakt 95 %-KI. */
export function clopperPearson(k, n, alpha = 0.05) {
  if (n === 0) return [null, null];
  return [k === 0 ? 0 : ibetaInv(alpha / 2, k, n - k + 1),
          k === n ? 1 : ibetaInv(1 - alpha / 2, k + 1, n - k)];
}
/** Wilson score-intervall (brukes i Newcombe-differansen). */
export function wilson(k, n, z = 1.959963984540054) {
  if (n === 0) return [null, null];
  const p = k / n, z2 = z * z, d = 1 + z2 / n;
  const c = p + z2 / (2 * n), h = z * Math.sqrt((p * (1 - p) + z2 / (4 * n)) / n);
  return [(c - h) / d, (c + h) / d];
}
/** Newcombe (metode 10) 95 %-KI for differansen p1 − p2. */
export function newcombe(k1, n1, k2, n2, z = 1.959963984540054) {
  const [l1, u1] = wilson(k1, n1, z), [l2, u2] = wilson(k2, n2, z);
  const d = k1 / n1 - k2 / n2;
  return [d - Math.sqrt((k1 / n1 - l1) ** 2 + (u2 - k2 / n2) ** 2),
          d + Math.sqrt((u1 - k1 / n1) ** 2 + (k2 / n2 - l2) ** 2)];
}

/** Fishers eksakte tosidige test for 2×2 (summerer alle tabeller med p ≤ p_obs). */
export function fisherEksakt(a, b, c, d) {
  const n = a + b + c + d, r1 = a + b, k1 = a + c;
  const lo = Math.max(0, k1 - (n - r1)), hi = Math.min(r1, k1);
  const lp = (x) => logChoose(r1, x) + logChoose(n - r1, k1 - x) - logChoose(n, k1);
  const p0 = lp(a), TOL = 1e-9;
  let p = 0;
  for (let x = lo; x <= hi; x++) { const q = lp(x); if (q <= p0 + TOL) p += Math.exp(q); }
  return Math.min(1, p);
}

/** Holm–Bonferroni: returnerer justerte p-verdier i inndatarekkefølge. */
export function holm(pverdier) {
  const idx = pverdier.map((p, i) => [p, i]).sort((x, y) => x[0] - y[0]);
  const m = pverdier.length, ut = new Array(m);
  let lopende = 0;
  idx.forEach(([p, i], r) => { lopende = Math.max(lopende, Math.min(1, (m - r) * p)); ut[i] = lopende; });
  return ut;
}

// ---------------------------------------------------------------------------
// 3. Overlevelses- og konkurrerende-risiko-estimatorer
// ---------------------------------------------------------------------------

/** Grupperer {t, arsak} i risikotabell sortert på tid. */
export function risikotabell(data) {
  const m = new Map();
  for (const r of data) {
    const e = m.get(r.t) || { t: r.t, d1: 0, d2: 0, c: 0 };
    if (r.arsak === 1) e.d1++; else if (r.arsak === 2) e.d2++; else e.c++;
    m.set(r.t, e);
  }
  const rader = [...m.values()].sort((a, b) => a.t - b.t);
  let n = data.length;
  for (const r of rader) { r.n = n; n -= r.d1 + r.d2 + r.c; }
  return rader;
}

/**
 * Aalen–Johansen-estimator for kumulativ insidens av årsak 1, med
 * varians etter deltametoden (Marubini & Valsecchi 1995 / Klein & Moeschberger):
 *
 *  V[F1(t)] = Σ [F1(t)−F1(ti)]² · di/(ni(ni−di))
 *           + Σ S(ti−)² · ((ni−d1i)/ni) · d1i/ni²
 *           − 2 Σ [F1(t)−F1(ti)] · S(ti−) · d1i/ni²
 *
 * Returnerer en trappefunksjon med F, S og de tre variansleddene kumulert,
 * slik at variansen kan evalueres i et vilkårlig t etterpå.
 */
export function aalenJohansen(data) {
  const rt = risikotabell(data).filter((r) => r.d1 + r.d2 > 0);
  let S = 1, F = 0;
  const steg = [];
  for (const r of rt) {
    const d = r.d1 + r.d2, n = r.n;
    const Sfor = S;
    F += Sfor * r.d1 / n;
    S *= 1 - d / n;
    steg.push({ t: r.t, n, d1: r.d1, d2: r.d2, d, Sfor, F,
      a: n > d ? d / (n * (n - d)) : 0,          // vekt til ledd 1
      b: Sfor * Sfor * ((n - r.d1) / n) * (r.d1 / (n * n)), // ledd 2
      c: Sfor * (r.d1 / (n * n)) });             // vekt til ledd 3
  }
  return { steg, n0: data.length };
}

/** F1(t) fra en AJ-trapp. */
export function ajF(aj, t) {
  let v = 0;
  for (const s of aj.steg) { if (s.t <= t) v = s.F; else break; }
  return v;
}
/** Varians av F1(t). */
export function ajVar(aj, t) {
  const F = ajF(aj, t);
  let s1 = 0, s2 = 0, s3 = 0;
  for (const s of aj.steg) {
    if (s.t > t) break;
    const g = F - s.F;
    s1 += g * g * s.a;
    s2 += s.b;
    s3 += g * s.c;
  }
  return Math.max(0, s1 + s2 - 2 * s3);
}
/** Antall i risiko rett før t (ordinær risikomengde). */
export function risikoVed(data, t) {
  return data.filter((r) => r.t >= t).length;
}
/**
 * 95 %-KI for F1(t). "loglog" = log(−log F)-transformasjon (standard for
 * kumulativ insidens, holder seg i (0,1)); "wald" = F ± z·SE.
 */
export function ajKI(aj, t, type = "loglog", z = 1.959963984540054) {
  const F = ajF(aj, t), V = ajVar(aj, t), se = Math.sqrt(V);
  if (F <= 0 || F >= 1) return [F, F, se];
  if (type === "wald") return [Math.max(0, F - z * se), Math.min(1, F + z * se), se];
  const seTheta = se / Math.abs(F * Math.log(F));
  return [Math.pow(F, Math.exp(z * seTheta)), Math.pow(F, Math.exp(-z * seTheta)), se];
}
/** Første tidspunkt der F1 ≥ p (kvantil i subfordelingen). null hvis aldri nådd. */
export function ajKvantil(aj, p) {
  for (const s of aj.steg) if (s.F >= p) return s.t;
  return null;
}
/**
 * KI for CIF-kvantilen ved testinversjon (Brookmeyer–Crowley-prinsippet):
 * nedre = første t der ØVRE KI-grense ≥ p; øvre = første t der NEDRE ≥ p.
 */
export function ajKvantilKI(aj, p, type = "loglog") {
  let lo = null, hi = null;
  for (const s of aj.steg) {
    const [l, u] = ajKI(aj, s.t, type);
    if (lo === null && u >= p) lo = s.t;
    if (hi === null && l >= p) hi = s.t;
  }
  return [lo, hi];
}

/** Kaplan–Meier for alle årsaker samlet (brukes i Grays risikomengde). */
export function kmAlle(data) {
  const rt = risikotabell(data);
  let S = 1; const steg = [];
  for (const r of rt) { const d = r.d1 + r.d2; if (d > 0) { steg.push({ t: r.t, Sfor: S }); S *= 1 - d / r.n; } }
  return steg;
}

// ---------------------------------------------------------------------------
// 4. Grays test (Gray 1988), ρ = 0
// ---------------------------------------------------------------------------
/**
 * Logrank-type test på SUBDISTRIBUSJONSRISIKOMENGDEN
 *   R_g(t) = Y_g(t) · (1 − F̂1g(t−)) / Ŝg(t−)
 * der Y_g er ordinær risikomengde, Ŝg er KM for alle årsaker og F̂1g er
 * AJ-estimatet for årsak 1 — begge estimert i gruppen selv (Gray 1988).
 * R_g teller altså også de som har hatt den konkurrerende hendelsen.
 *
 * U = Σ_k [ d1_{1k} − (R_1k/R_k)·d1_k ]
 * V = Σ_k (R_1k R_2k / R_k²) · d1_k · (R_k − d1_k)/(R_k − 1)
 * z = U/√V,  p = tosidig normal.
 */
export function grayRutenett(alle) {
  const tider = [...new Set(alle.map((r) => r.t))].sort((a, b) => a - b);
  return { tider, idx: new Map(tider.map((t, i) => [t, i])) };
}
/** Bygger R_g(t) og d1_g(t) på et felles tidsrutenett. */
function graySpor(g, rut) {
  const T = rut.tider.length;
  const d1 = new Float64Array(T), d2 = new Float64Array(T), c = new Float64Array(T);
  for (const r of g) {
    const i = rut.idx.get(r.t);
    if (r.arsak === 1) d1[i]++; else if (r.arsak === 2) d2[i]++; else c[i]++;
  }
  const R = new Float64Array(T);
  let n = g.length, S = 1, F = 0;
  for (let i = 0; i < T; i++) {
    R[i] = S > 0 && n > 0 ? (n * (1 - F)) / S : 0;
    const d = d1[i] + d2[i];
    if (n > 0) { F += (S * d1[i]) / n; S *= 1 - d / n; }
    n -= d + c[i];
  }
  return { R, d1 };
}
export function grayTest(gruppe1, gruppe2, rut = null) {
  const r = rut || grayRutenett([...gruppe1, ...gruppe2]);
  const a = graySpor(gruppe1, r), b = graySpor(gruppe2, r);
  let U = 0, V = 0;
  for (let i = 0; i < r.tider.length; i++) {
    const dt = a.d1[i] + b.d1[i];
    if (dt === 0) continue;
    const Rt = a.R[i] + b.R[i];
    if (Rt <= 1) continue;
    U += a.d1[i] - (a.R[i] / Rt) * dt;
    V += ((a.R[i] * b.R[i]) / (Rt * Rt)) * dt * ((Rt - dt) / (Rt - 1));
  }
  const z = U / Math.sqrt(V);
  return { U, V, z, p: pTosidigZ(z) };
}

// ---------------------------------------------------------------------------
// 5. Stratifisert logrank + Cox
// ---------------------------------------------------------------------------
/**
 * Stratifisert logrank (hendelse = årsak 1; alt annet sensurert ved t).
 * Returnerer O−E, V, z, samt logrank-basert HR = exp((O−E)/V) med
 * 95 %-KI exp((O−E)/V ± 1,96/√V)  (Peto/one-step-estimatoren).
 */
export function logrankStratifisert(data, gruppeAv, strataAv) {
  const strata = new Map();
  for (const r of data) {
    const s = strataAv(r);
    if (!strata.has(s)) strata.set(s, []);
    strata.get(s).push(r);
  }
  let OE = 0, V = 0, O1 = 0, E1 = 0, brukt = 0;
  for (const [, s] of strata) {
    const m = new Map();
    for (const r of s) {
      const e = m.get(r.t) || { t: r.t, d: 0, d1: 0, n: 0, n1: 0 };
      if (r.arsak === 1) { e.d++; if (gruppeAv(r)) e.d1++; }
      m.set(r.t, e);
    }
    const tider = [...m.values()].sort((a, b) => a.t - b.t);
    let n = s.length, n1 = s.filter(gruppeAv).length;
    let i = 0;
    const sort = s.slice().sort((a, b) => a.t - b.t);
    for (const e of tider) {
      while (i < sort.length && sort[i].t < e.t) { if (gruppeAv(sort[i])) n1--; n--; i++; }
      e.n = n; e.n1 = n1;
      if (e.d > 0 && n > 1 && n1 > 0 && n1 < n) {
        O1 += e.d1; E1 += e.d * n1 / n;
        OE += e.d1 - e.d * n1 / n;
        V += (e.d * (n1 / n) * (1 - n1 / n) * (n - e.d)) / (n - 1);
        brukt++;
      }
      // fjern hendelsene på e.t (og sensurerte på e.t) i neste runde
      while (i < sort.length && sort[i].t === e.t) { if (gruppeAv(sort[i])) n1--; n--; i++; }
    }
  }
  const z = OE / Math.sqrt(V), b = OE / V, se = 1 / Math.sqrt(V);
  return { O: O1, E: E1, OE, V, z, p: pTosidigZ(z), strata: strata.size, hendelsestider: brukt,
    hr: Math.exp(b), hr_lav: Math.exp(b - 1.959963984540054 * se), hr_hoy: Math.exp(b + 1.959963984540054 * se) };
}

/**
 * Stratifisert Cox med ÉN binær kovariat, Breslow-ties, Newton–Raphson.
 * Returnerer β̂, modellbasert SE, robust (klynge-) SE og Schoenfeld-residualer.
 */
export function coxStratifisertBinaer(data, x, strataAv, klyngeAv = null) {
  const strata = new Map();
  for (const r of data) {
    const s = strataAv(r);
    if (!strata.has(s)) strata.set(s, []);
    strata.get(s).push(r);
  }
  const blokker = [...strata.values()].map((s) => s.slice().sort((a, b) => b.t - a.t)); // synkende tid

  const uv = (beta) => {
    let U = 0, I = 0;
    for (const s of blokker) {
      let S0 = 0, S1 = 0; // risikosummer, akkumuleres bakfra
      let i = 0;
      while (i < s.length) {
        const t = s[i].t;
        let j = i;
        while (j < s.length && s[j].t === t) { const w = Math.exp(beta * x(s[j])); S0 += w; S1 += w * x(s[j]); j++; }
        let d = 0, sx = 0;
        for (let k = i; k < j; k++) if (s[k].arsak === 1) { d++; sx += x(s[k]); }
        if (d > 0 && S0 > 0) {
          const m = S1 / S0;
          U += sx - d * m;
          I += d * (S1 / S0 - m * m); // binær x: E[x²]=E[x]
        }
        i = j;
      }
    }
    return { U, I };
  };
  let beta = 0;
  for (let it = 0; it < 60; it++) {
    const { U, I } = uv(beta);
    if (I <= 0) break;
    const step = U / I;
    beta += step;
    if (Math.abs(step) < 1e-12) break;
  }
  const { I } = uv(beta);
  const se = 1 / Math.sqrt(I);

  // Schoenfeld-residualer + per-hendelse-varians (til PH-diagnostikk)
  // og score-residualer (til robust sandwich).
  const schoen = [];
  const score = new Map(); // nøkkel -> sum
  for (const s of blokker) {
    let S0 = 0, S1 = 0, i = 0;
    const bidrag = []; // {r, dM-ledd}
    while (i < s.length) {
      const t = s[i].t; let j = i;
      while (j < s.length && s[j].t === t) { const w = Math.exp(beta * x(s[j])); S0 += w; S1 += w * x(s[j]); j++; }
      let d = 0;
      for (let k = i; k < j; k++) if (s[k].arsak === 1) d++;
      if (d > 0 && S0 > 0) {
        const m = S1 / S0, V = S1 / S0 - m * m;
        for (let k = i; k < j; k++) if (s[k].arsak === 1) schoen.push({ t, r: x(s[k]) - m, V });
        bidrag.push({ t, m, d, S0, iFra: i });
      }
      i = j;
    }
    // score-residualer: U_i = Σ_k [ dN_i(tk)(x_i−m_k) − w_i (x_i−m_k) dk/S0_k ]
    for (const r of s) {
      let u = 0;
      const w = Math.exp(beta * x(r));
      for (const b of bidrag) {
        if (b.t <= r.t) u -= w * (x(r) - b.m) * b.d / b.S0;
        if (b.t === r.t && r.arsak === 1) u += (x(r) - b.m);
      }
      const key = klyngeAv ? klyngeAv(r) : r;
      score.set(key, (score.get(key) || 0) + u);
    }
  }
  let meat = 0;
  for (const [, u] of score) meat += u * u;
  const robustSe = Math.sqrt(meat) / I;

  return { beta, se, robustSe, I, schoen, strata: strata.size,
    hr: Math.exp(beta),
    hr_lav: Math.exp(beta - 1.959963984540054 * se), hr_hoy: Math.exp(beta + 1.959963984540054 * se),
    hr_lav_rob: Math.exp(beta - 1.959963984540054 * robustSe),
    hr_hoy_rob: Math.exp(beta + 1.959963984540054 * robustSe),
    z: beta / se, p: pTosidigZ(beta / se),
    z_rob: beta / robustSe, p_rob: pTosidigZ(beta / robustSe) };
}

/**
 * Grambsch–Therneau-type PH-test for én kovariat: scoretest for θ i
 * β(t) = β + θ·(g(t) − ḡ), basert på Schoenfeld-residualene.
 *   T = (Σ (g_k − ḡ) s_k)² / (Σ (g_k − ḡ)² V_k) ~ χ²(1)
 * g = "rang" (rangert hendelsestid, som cox.zph sin standard) eller "log".
 */
export function phTest(schoen, transform = "rang") {
  const s = schoen.slice().sort((a, b) => a.t - b.t);
  const g = s.map((e, i) => (transform === "log" ? Math.log(Math.max(1, e.t)) :
                             transform === "tid" ? e.t : i + 1));
  const gm = g.reduce((a, b) => a + b, 0) / g.length;
  let U = 0, V = 0, sgg = 0, srr = 0;
  s.forEach((e, i) => { const gc = g[i] - gm; U += gc * e.r; V += gc * gc * e.V; sgg += gc * gc; srr += e.r * e.r; });
  const T = (U * U) / V;
  return { T, df: 1, p: pKhi(T, 1),
    korrelasjon: U / Math.sqrt(sgg * srr), // Pearson(g, Schoenfeld-residual)
    hendelser: s.length, transform };
}

// ---------------------------------------------------------------------------
// 6. Tilfeldighet: reproduserbar RNG (mulberry32)
// ---------------------------------------------------------------------------
export function rng(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export const kvantil = (sortert, p) => {
  if (!sortert.length) return null;
  const i = (sortert.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i);
  return lo === hi ? sortert[lo] : sortert[lo] + (sortert[hi] - sortert[lo]) * (i - lo);
};

// ---------------------------------------------------------------------------
// 7. Skriving
// ---------------------------------------------------------------------------
export function skrivJson(rel, obj) {
  const full = path.join(ROOT, rel).replace(/\\/g, "/");
  mkdirSync(path.dirname(full), { recursive: true });
  const body = JSON.stringify(obj, null, 2) + "\n";
  writeFileSync(full, body, "utf8");
  const sha = createHash("sha256").update(body).digest("hex");
  console.log(`  skrevet ${rel}  sha256=${sha}`);
  return { path: full, sha256: sha };
}
export const r1 = (x) => (x === null || x === undefined ? null : +(+x).toFixed(1));
export const r2 = (x) => (x === null || x === undefined ? null : +(+x).toFixed(2));
export const r3 = (x) => (x === null || x === undefined ? null : +(+x).toFixed(3));
export const r4 = (x) => (x === null || x === undefined ? null : +(+x).toFixed(4));
export const pst = (x, d = 1) => (x === null || x === undefined ? null : +(100 * x).toFixed(d));
