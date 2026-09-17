// LANE 3 — statistikkrutiner uten eksterne avhengigheter.
// Wilson- og Clopper-Pearson-intervall, Kaplan-Meier, stratifisert logrank
// (Mantel-Haenszel) og direkte standardisering av overlevelseskurver.
// Ingen databasekontakt her — ren matematikk, importeres av analyseskriptene.

// ---------- regularisert ufullstendig betafunksjon ----------
function logGamma(x) {
  const c = [76.18009172947146, -86.50532032941677, 24.01409824083091,
             -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5];
  let y = x, tmp = x + 5.5;
  tmp -= (x + 0.5) * Math.log(tmp);
  let ser = 1.000000000190015;
  for (let j = 0; j < 6; j++) ser += c[j] / ++y;
  return -tmp + Math.log(2.5066282746310005 * ser / x);
}

function betacf(a, b, x) {
  const FPMIN = 1e-300, EPS = 3e-16;
  const qab = a + b, qap = a + 1, qam = a - 1;
  let c = 1, d = 1 - qab * x / qap;
  if (Math.abs(d) < FPMIN) d = FPMIN;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= 300; m++) {
    const m2 = 2 * m;
    let aa = m * (b - m) * x / ((qam + m2) * (a + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; h *= d * c;
    aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    const del = d * c; h *= del;
    if (Math.abs(del - 1) < EPS) break;
  }
  return h;
}

/** I_x(a,b) — regularisert ufullstendig beta. */
export function betaInc(a, b, x) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const bt = Math.exp(logGamma(a + b) - logGamma(a) - logGamma(b)
                      + a * Math.log(x) + b * Math.log(1 - x));
  return x < (a + 1) / (a + b + 2) ? bt * betacf(a, b, x) / a
                                   : 1 - bt * betacf(b, a, 1 - x) / b;
}

/** Invers av I_x(a,b) ved bisksjon — nok presisjon for konfidensgrenser. */
export function betaInv(p, a, b) {
  let lo = 0, hi = 1;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (betaInc(a, b, mid) < p) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
}

/** Clopper-Pearson (eksakt) 100(1-alpha)% intervall for en andel. */
export function clopperPearson(k, n, alpha = 0.05) {
  if (n === 0) return [NaN, NaN];
  const lo = k === 0 ? 0 : betaInv(alpha / 2, k, n - k + 1);
  const hi = k === n ? 1 : betaInv(1 - alpha / 2, k + 1, n - k);
  return [lo, hi];
}

/** Wilson score-intervall (uten kontinuitetskorreksjon). */
export function wilson(k, n, z = 1.959963984540054) {
  if (n === 0) return [NaN, NaN];
  const p = k / n, z2 = z * z;
  const denom = 1 + z2 / n;
  const centre = (p + z2 / (2 * n)) / denom;
  const half = z * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom;
  return [Math.max(0, centre - half), Math.min(1, centre + half)];
}

/** Normalfordelingens halefunksjon (tosidig p-verdi fra en z-verdi). */
export function twoSidedP(z) {
  const t = 1 / (1 + 0.2316419 * Math.abs(z));
  const d = 0.3989422804014327 * Math.exp(-z * z / 2);
  const p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937
            + t * (-1.821255978 + t * 1.330274429))));
  return 2 * p;
}

/** Empiriske kvartiler (type 7, som R's default) på et sortert tallarray. */
export function quantileSorted(sorted, q) {
  const n = sorted.length;
  if (n === 0) return NaN;
  if (n === 1) return sorted[0];
  const h = (n - 1) * q;
  const lo = Math.floor(h), hi = Math.ceil(h);
  return sorted[lo] + (h - lo) * (sorted[hi] - sorted[lo]);
}

// ---------- overlevelsesanalyse ----------
/**
 * Kaplan-Meier. rows = [{t, event}] der event=1 er hendelsen (innstilling),
 * event=0 er sensurering. Returnerer {times, surv, atRisk, events}.
 */
export function kaplanMeier(rows) {
  const byT = new Map();
  for (const r of rows) {
    const e = byT.get(r.t) || { d: 0, c: 0 };
    if (r.event) e.d++; else e.c++;
    byT.set(r.t, e);
  }
  const times = [...byT.keys()].sort((a, b) => a - b);
  let n = rows.length, s = 1;
  const out = { times: [], surv: [], atRisk: [], events: [] };
  for (const t of times) {
    const { d, c } = byT.get(t);
    if (d > 0) s *= 1 - d / n;
    out.times.push(t); out.surv.push(s); out.atRisk.push(n); out.events.push(d);
    n -= d + c;
  }
  return out;
}

/** Median (eller annen kvantil) lest av en KM-kurve. NaN hvis ikke nådd. */
export function kmQuantile(km, q = 0.5) {
  const target = 1 - q;
  for (let i = 0; i < km.times.length; i++) if (km.surv[i] <= target) return km.times[i];
  return NaN;
}

/**
 * Stratifisert logrank (Mantel-Haenszel) for to grupper.
 * strata: Map<stratum, {a: rows, b: rows}> med rows = [{t, event}].
 * Returnerer O-E for gruppe a, varians, z, p og HR (Peto).
 */
export function stratifiedLogrank(strata) {
  let O = 0, E = 0, V = 0;
  for (const [, g] of strata) {
    const all = [...g.a.map((r) => ({ ...r, g: 0 })), ...g.b.map((r) => ({ ...r, g: 1 }))];
    if (!all.length) continue;
    const times = [...new Set(all.filter((r) => r.event).map((r) => r.t))].sort((x, y) => x - y);
    let nA = g.a.length, nB = g.b.length;
    const sorted = all.slice().sort((x, y) => x.t - y.t);
    let idx = 0;
    for (const t of times) {
      while (idx < sorted.length && sorted[idx].t < t) {
        if (sorted[idx].g === 0) nA--; else nB--;
        idx++;
      }
      const dA = all.filter((r) => r.t === t && r.event && r.g === 0).length;
      const dB = all.filter((r) => r.t === t && r.event && r.g === 1).length;
      const d = dA + dB, n = nA + nB;
      if (n <= 1 || d === 0) continue;
      O += dA;
      E += d * nA / n;
      V += d * (nA / n) * (nB / n) * ((n - d) / (n - 1));
    }
  }
  const z = V > 0 ? (O - E) / Math.sqrt(V) : NaN;
  return { O, E, V, z, p: twoSidedP(z), hr: V > 0 ? Math.exp((O - E) / V) : NaN };
}

/**
 * Direkte standardisering: bygg gruppe b sin KM-kurve om til den
 * strata-miksen gruppe a har. Returnerer {times, surv}.
 */
export function standardisedKM(strata, weightsFrom = "a", target = "b") {
  const strataKeys = [...strata.keys()];
  const w = new Map();
  let wsum = 0;
  for (const k of strataKeys) {
    const n = strata.get(k)[weightsFrom].length;
    w.set(k, n); wsum += n;
  }
  const kms = new Map();
  const allTimes = new Set();
  for (const k of strataKeys) {
    const rows = strata.get(k)[target];
    if (!rows.length || !w.get(k)) continue;
    const km = kaplanMeier(rows);
    kms.set(k, km);
    for (const t of km.times) allTimes.add(t);
  }
  const times = [...allTimes].sort((a, b) => a - b);
  const surv = [];
  // strata uten data i målgruppa faller ut av vekten
  let usable = 0;
  for (const k of kms.keys()) usable += w.get(k);
  for (const t of times) {
    let s = 0;
    for (const [k, km] of kms) {
      let v = 1;
      for (let i = 0; i < km.times.length; i++) { if (km.times[i] <= t) v = km.surv[i]; else break; }
      s += (w.get(k) / usable) * v;
    }
    surv.push(s);
  }
  return { times, surv, vektgrunnlag: usable, wsum };
}
