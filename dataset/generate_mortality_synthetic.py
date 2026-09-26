#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClimateGuard India - SYNTHETIC heat-related mortality dataset generator.

*** EVERY VALUE PRODUCED HERE IS SYNTHETIC. NOTHING IS NCRB / IMD / OFFICIAL DATA. ***

Statistical reference: Guin P, Bhan N, Sethi K (2025). "Mortality due to heatstroke and
exposure to cold: Evidence from India". Temperature 12(2):179-199.

Usage:
    python generate_mortality_synthetic.py --generation-date 2026-09-24 --out .
Default window = the most recent completed 365 days before the generation date.
"""
import argparse, json, math, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SEED = 20260924
WARMUP = 14                      # burn-in days so lag-7 features are valid on day 1
STATES = ["Tamil Nadu", "Kerala", "Karnataka"]
CELLS = ["M<30", "F<30", "M30-59", "F30-59", "M60+", "F60+"]
# Paper Table 1 means (heatstroke deaths per state-year): M<30=4, F<30=1, M30-59=19, F30-59=4, M60+=8, F60+=3 (sum 39)
PAPER_CELL_MEANS = np.array([4, 1, 19, 4, 8, 3], float)
PAPER_REL_SENS = 8.028 / 39.0    # +8.028 deaths per +1C asmt, relative to mean 39 deaths/state-year
PAPER_CUM = {"Tamil Nadu": 228, "Karnataka": 97, "Kerala": 10}

# ---------------------------------------------------------------- state profiles (ASSUMPTIONS)
PROFILES = {
    "Tamil Nadu": dict(
        tmax_mean=34.0, tmax_amp=3.0, peak=130, sw_dip=0.8, ne_dip=2.0, w_dip=1.5,
        anom_sd=1.2, anom_phi=0.65, rh_base=68, rh_dry_amp=10, rh_sw=3, rh_ne=4,
        dtr=8.5, wind=2.6, wind_sw=0.15, sun_sw=0.20, sun_ne=0.30,
        events=3.5, event_amp=(2.0, 4.5), event_rh=2.0,
        hw_tmax=37.5, hw_anom=2.0, hot_tmax=36.5,
        population=77_000_000, elderly=13.0, u30=47.0, wa=40.0, outdoor=0.36, urban=55.0,
        healthcare=0.78, hap=0.60, cooling=0.55, phr_base=0.55, target_heatstroke=24.0),
    "Kerala": dict(
        tmax_mean=32.2, tmax_amp=1.3, peak=85, sw_dip=3.2, ne_dip=0.8, w_dip=0.8,
        anom_sd=0.9, anom_phi=0.65, rh_base=74, rh_dry_amp=6, rh_sw=12, rh_ne=4,
        dtr=6.5, wind=2.2, wind_sw=0.70, sun_sw=0.55, sun_ne=0.20,
        events=2.0, event_amp=(1.5, 3.0), event_rh=0.8,
        hw_tmax=35.0, hw_anom=1.8, hot_tmax=33.5,
        population=35_800_000, elderly=17.0, u30=38.0, wa=45.0, outdoor=0.28, urban=50.0,
        healthcare=0.85, hap=0.65, cooling=0.55, phr_base=0.60, target_heatstroke=5.0),
    "Karnataka": dict(
        tmax_mean=32.0, tmax_amp=3.2, peak=108, sw_dip=3.0, ne_dip=0.5, w_dip=1.5,
        anom_sd=1.5, anom_phi=0.65, rh_base=62, rh_dry_amp=12, rh_sw=18, rh_ne=3,
        dtr=10.0, wind=2.8, wind_sw=0.60, sun_sw=0.45, sun_ne=0.10,
        events=3.0, event_amp=(2.0, 4.5), event_rh=2.5,
        hw_tmax=36.5, hw_anom=2.0, hot_tmax=35.5,
        population=68_000_000, elderly=11.5, u30=50.0, wa=38.5, outdoor=0.45, urban=42.0,
        healthcare=0.70, hap=0.55, cooling=0.50, phr_base=0.50, target_heatstroke=12.0),
}

CFG = dict(
    seasonality_strength=0.9,
    other_to_heatstroke_ratio=3.0,
    hazard_T_segments=[(32, 35, 0.04), (35, 38, 0.12), (38, 40, 0.30), (40, 99, 0.55)],
    hazard_W_segments=[(26, 28, 0.05), (28, 30, 0.15), (30, 32, 0.35), (32, 35, 0.70), (35, 99, 1.20)],
    wbgt_weight=0.5,
    shock_phi=0.3,
    heat=dict(lag_w=[1.0, 0.6, 0.35, 0.2, 0.05], beta_mult=1.0, hum=0.35, dur=0.04, night=0.25,
              vul=1.2, out=0.8, phr=-0.35, cool=-0.30, nb_size=1.5, shock_sd=0.30, kappa=30),
    other=dict(lag_w=[0.6, 0.6, 0.45, 0.30, 0.15], beta_mult=0.6, hum=0.5, dur=0.05, night=0.45,
               vul=1.5, out=0.3, phr=-0.25, cool=-0.30, nb_size=2.0, shock_sd=0.30, kappa=20),
    other_cell_base=[0.05, 0.03, 0.27, 0.12, 0.30, 0.23],
)

# ---------------------------------------------------------------- physics helpers
def bump(doy, c, s):
    d = np.abs(doy - c); d = np.minimum(d, 365 - d)
    return np.exp(-0.5 * (d / s) ** 2)

def piecewise(x, segs):
    out = np.zeros_like(x, dtype=float)
    for lo, hi, sl in segs:
        out += sl * np.clip(x - lo, 0, hi - lo)
    return out

def run_length(flag):
    out = np.zeros(len(flag), int); c = 0
    for i, f in enumerate(flag):
        c = c + 1 if f else 0
        out[i] = c
    return out

def lag(x, k):
    o = np.full(len(x), np.nan); o[k:] = x[:-k]; return o

def ar1(rng, n, phi, sd):
    e = rng.normal(0, sd * np.sqrt(1 - phi ** 2), n); x = np.zeros(n); x[0] = rng.normal(0, sd)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x

def esat(T): return 6.1094 * np.exp(17.625 * T / (T + 243.04))

def dewpoint(T, RH):
    g = np.log(np.clip(RH, 1, 100) / 100) + 17.625 * T / (243.04 + T)
    return 243.04 * g / (17.625 - g)

def stull_wet_bulb(T, RH):
    return (T * np.arctan(0.151977 * np.sqrt(RH + 8.313659)) + np.arctan(T + RH) - np.arctan(RH - 1.676331)
            + 0.00391838 * RH ** 1.5 * np.arctan(0.023101 * RH) - 4.686035)

def heat_index_f(T, RH):
    """NWS Rothfusz regression. Input/Output in DEGREES FAHRENHEIT."""
    simple = 0.5 * (T + 61.0 + (T - 68.0) * 1.2 + RH * 0.094)
    avg = (simple + T) / 2
    hi = (-42.379 + 2.04901523 * T + 10.14333127 * RH - 0.22475541 * T * RH - 0.00683783 * T * T
          - 0.05481717 * RH * RH + 0.00122874 * T * T * RH + 0.00085282 * T * RH * RH - 0.00000199 * T * T * RH * RH)
    a1 = np.where((RH < 13) & (T >= 80) & (T <= 112),
                  -((13 - RH) / 4) * np.sqrt(np.clip((17 - np.abs(T - 95)) / 17, 0, None)), 0.0)
    a2 = np.where((RH > 85) & (T >= 80) & (T <= 87), ((RH - 85) / 10) * ((87 - T) / 5), 0.0)
    return np.where(avg >= 80, hi + a1 + a2, simple)

def wbgt_category(w):
    return np.select([w < 28, w < 30, w < 32, w <= 35], ["LOW", "CAUTION", "DANGER", "EXTREME"], "SEVERE")

def thermal_chain(tmax, tmin, rh, wind, sun):
    """Daily thermal indices from Tmax/Tmin/mean RH/wind/sunshine. Hourly WBGT via Stull wet-bulb + simple globe increment."""
    tmean = (tmax + tmin) / 2
    td = dewpoint(tmean, rh)
    h = np.arange(24)[None, :]
    Th = ((tmax + tmin) / 2)[:, None] + ((tmax - tmin) / 2)[:, None] * np.cos(2 * np.pi * (h - 15) / 24)
    RHh = np.clip(100 * esat(td)[:, None] / esat(Th), 5, 99)
    Tw = stull_wet_bulb(Th, RHh)
    sol = np.where((h >= 6) & (h <= 18), np.sin(np.pi * (h - 6) / 12), 0.0)
    inc = np.clip(7.0 - 0.6 * wind, 2.0, 7.0) * sun
    Tg = Th + inc[:, None] * sol
    wb = 0.7 * Tw + 0.2 * Tg + 0.1 * Th
    hi_f = heat_index_f(tmax * 9 / 5 + 32, RHh[:, 15])
    return dict(tmean=tmean, td=td, wbgt=wb.max(1), dur=(wb >= 30).sum(1), hrs35=(Th >= 35).sum(1),
                hi_f=hi_f, hi_c=(hi_f - 32) * 5 / 9)

# ---------------------------------------------------------------- weather generator
def gen_weather(state, dates, rng):
    p = PROFILES[state]; n = len(dates); doy = dates.dayofyear.values.astype(float)
    sw = bump(doy, 200, 32); ne = bump(doy, 305, 25); wn = bump(doy, 20, 30)
    ang = 2 * np.pi * (doy - p["peak"]) / 365.25
    tclim = p["tmax_mean"] + p["tmax_amp"] * np.cos(ang) - p["sw_dip"] * sw - p["ne_dip"] * ne - p["w_dip"] * wn
    rhclim = p["rh_base"] - p["rh_dry_amp"] * np.cos(ang) + p["rh_sw"] * sw + p["rh_ne"] * ne
    tanom = ar1(rng, n, p["anom_phi"], p["anom_sd"])
    ev = np.zeros(n); idxs = np.where((doy >= 50) & (doy <= 170))[0]
    if len(idxs) > 10:
        for _ in range(rng.poisson(p["events"] * len(idxs) / 121.0)):
            s = int(rng.choice(idxs)); L = int(rng.integers(3, 10)); amp = rng.uniform(*p["event_amp"])
            prof = np.sin(np.linspace(0, np.pi, L + 2))[1:-1]; prof = prof / prof.max()
            e = min(L, n - s); ev[s:s + e] = np.maximum(ev[s:s + e], amp * prof[:e])
    tmax = tclim + tanom + ev
    rh = np.clip(rhclim + ar1(rng, n, 0.7, 5.0) - 1.2 * tanom - p["event_rh"] * ev, 25, 98)
    dtr = np.clip(p["dtr"] * (1 + 0.010 * (65 - rh)) * (1 - 0.20 * sw) + rng.normal(0, 0.8, n), 3.0, 15.0)
    tmin = tmax - dtr
    wind = np.clip(rng.gamma(4.0, p["wind"] / 4.0, n) * (1 + p["wind_sw"] * sw), 0.3, 9.0)
    sun = np.clip(0.92 - p["sun_sw"] * sw - p["sun_ne"] * ne - 0.3 * np.clip(rh - 78, 0, None) / 20
                  + rng.normal(0, 0.07, n), 0.2, 1.0)
    return dict(tmax=tmax, tmin=tmin, rh=rh, wind=wind, sun=sun, tclim=tclim, rhclim=rhclim, event=ev,
                n_uhi=rng.normal(0, 0.02, n), n_out=rng.normal(0, 0.03, n), n_vul=ar1(rng, n, 0.98, 0.02),
                n_phr=rng.normal(0, 0.02, n), n_hc=ar1(rng, n, 0.99, 0.01), n_cool=ar1(rng, n, 0.99, 0.02))

def uhi_from(tmax, w, p):
    return np.clip(0.8 * p["urban"] / 100 + 0.12 * np.clip((tmax - 32) / 8, 0, 1) + w["n_uhi"], 0, 1)

def compute_drivers(w, uhi, shift_mask=None, dT=0.0):
    tmax = w["tmax"].copy(); tmin = w["tmin"].copy()
    if shift_mask is not None:
        tmax[shift_mask] += dT; tmin[shift_mask] += dT
    ch = thermal_chain(tmax, tmin, w["rh"], w["wind"], w["sun"])
    ww = CFG["wbgt_weight"]
    X = (1 - ww) * piecewise(tmax, CFG["hazard_T_segments"]) + ww * piecewise(ch["wbgt"], CFG["hazard_W_segments"])
    night_min = tmin + 1.5 * uhi
    dr = dict(ch); dr.update(tmax=tmax, tmin=tmin, X=X, X1=lag(X, 1), X2=lag(X, 2), X3=lag(X, 3), X7=lag(X, 7),
                              cum3=pd.Series(X).rolling(3).sum().values, cum7=pd.Series(X).rolling(7).sum().values,
                              night_min=night_min, night=np.clip((night_min - 24) / 6, 0, 1),
                              hum=np.clip((ch["td"] - 18) / 8, 0, 1))
    return dr

def compute_context(state, dates, w, dr, uhi):
    p = PROFILES[state]; doy = dates.dayofyear.values.astype(float)
    anom = w["tmax"] - w["tclim"]
    hw = (w["tmax"] >= p["hw_tmax"]) & (anom >= p["hw_anom"])
    hot = w["tmax"] >= p["hot_tmax"]
    sw = bump(doy, 200, 32); ne = bump(doy, 305, 25)
    wk = np.where(dates.weekday == 6, 0.78, np.where(dates.weekday == 5, 0.92, 1.0))
    out = np.clip(p["outdoor"] / 0.6 * wk * (1 - 0.30 * sw - 0.05 * ne) + w["n_out"], 0, 1)
    vbase = 0.35 * p["elderly"] / 20 + 0.25 * p["outdoor"] / 0.6 + 0.25 * (1 - p["healthcare"]) + 0.15 * (1 - p["cooling"])
    vul = np.clip(vbase + w["n_vul"], 0, 1)
    hw_recent = pd.Series(hw.astype(int)).rolling(3, min_periods=1).max().values
    phr = np.clip(p["phr_base"] + 0.15 * hw_recent + w["n_phr"], 0, 1)
    maxpop = max(q["population"] for q in PROFILES.values())
    return dict(doy=doy, anom=anom, hum_anom=w["rh"] - w["rhclim"], hw=hw, hot=hot,
                consec_hot=run_length(hot), consec_heat=run_length(dr["wbgt"] >= 30),
                out=out, vul=vul, phr=phr, uhi=uhi,
                hc=np.clip(p["healthcare"] + w["n_hc"], 0, 1), cool=np.clip(p["cooling"] + w["n_cool"], 0, 1),
                hap=np.full(len(doy), p["hap"]),
                popexp=np.clip(0.5 * p["population"] / maxpop + 0.3 * p["urban"] / 100 + 0.2 * out, 0, 1),
                season_peak=p["peak"])

def cut(d): return {k: (v[WARMUP:] if isinstance(v, np.ndarray) else v) for k, v in d.items()}

def mu_raw(dr, ctx, beta, kind):
    c = CFG[kind]; lw = c["lag_w"]
    eff = lw[0] * dr["X"] + lw[1] * dr["X1"] + lw[2] * dr["X2"] + lw[3] * dr["X3"] + lw[4] * dr["X7"]
    Xc = np.minimum(dr["X"], 1.0)
    eta = (beta * c["beta_mult"]) * eff + c["hum"] * dr["hum"] * Xc + c["dur"] * dr["dur"] + c["night"] * dr["night"] * Xc \
        + c["vul"] * (ctx["vul"] - 0.5) + c["out"] * (ctx["out"] - 0.5) + c["phr"] * (ctx["phr"] - 0.5) \
        + c["cool"] * (ctx["cool"] - 0.5) \
        + CFG["seasonality_strength"] * np.cos(2 * np.pi * (ctx["doy"] - ctx["season_peak"]) / 365.25)
    return np.exp(eta)

def split_cells(rng, total, base_p, adjust, kappa):
    w = base_p[None, :] * np.exp(adjust); w = w / w.sum(1, keepdims=True)
    g = rng.gamma(kappa * w, 1.0); p = g / g.sum(1, keepdims=True)
    out = np.zeros((len(total), 6), int)
    for i, t in enumerate(total):
        if t > 0:
            out[i] = rng.multinomial(int(t), p[i])
    return out

def cell_adjust(ctx, dr):
    n = len(ctx["out"]); a = np.zeros((n, 6))
    so = 2.0 * (ctx["out"] - ctx["out"].mean())
    nz = 0.5 * (dr["night"] - dr["night"].mean()) + 0.4 * (dr["hum"] - dr["hum"].mean())
    fz = 0.4 * (dr["night"] - dr["night"].mean())
    a[:, 2] += so; a[:, 4] += nz; a[:, 5] += nz; a[:, 1] += fz; a[:, 3] += fz; a[:, 5] += fz
    return a

# ---------------------------------------------------------------- similarity engine
SIG_COLS = {"max_temperature_c": "maximum_temperature_c", "mean_temperature_c": "mean_temperature_c",
            "humidity_percent": "relative_humidity_percent", "wbgt_c": "wbgt_c", "heat_index_c": "heat_index_c",
            "heat_duration_hours": "heat_duration_hours", "consecutive_heat_days": "consecutive_heat_days"}
SIG_W = {"wbgt_c": .25, "max_temperature_c": .15, "mean_temperature_c": .10, "humidity_percent": .15,
         "heat_index_c": .15, "heat_duration_hours": .10, "consecutive_heat_days": .10}

def find_similar_days(df, query, k=5, state=None):
    """Weighted, standardised multi-dimensional distance. Needs >=3 signature fields (never temperature alone)."""
    keys = [q for q in SIG_COLS if query.get(q) is not None]
    if len(keys) < 3:
        raise ValueError("Provide at least 3 thermal-signature fields; single-variable matching is not allowed.")
    pool = df if state is None else df[df.state == state]
    w = np.array([SIG_W[q] for q in keys]); w = w / w.sum()
    sd = np.array([df[SIG_COLS[q]].std() for q in keys])
    Z = (pool[[SIG_COLS[q] for q in keys]].values - np.array([query[q] for q in keys], float)) / sd
    d = np.sqrt((w * Z ** 2).sum(1))
    res = pool.assign(similarity_score=100 * np.exp(-d), distance=d).sort_values("distance")
    return res.head(k), keys

def analyse_scenario(df, query, k=5, k_stable=25):
    top, keys = find_similar_days(df, query, k)
    stable, _ = find_similar_days(df, query, k_stable)
    band = wbgt_category(np.array([query["wbgt_c"]]))[0] if query.get("wbgt_c") is not None else "n/a"
    ages = stable[["heat_related_deaths_under_30", "heat_related_deaths_30_59", "heat_related_deaths_60_plus"]].sum()
    sx = stable[["heat_related_deaths_male", "heat_related_deaths_female"]].sum()
    prec = {"LOW": "Routine hydration; no special measures.",
            "CAUTION": "Hydrate, schedule strenuous outdoor work outside the afternoon, watch vulnerable people.",
            "DANGER": "Limit outdoor work 11:00-16:00, mandatory shade/water breaks, check on elderly and outdoor workers.",
            "EXTREME": "Suspend non-essential outdoor labour in peak hours, open cooling shelters, alert hospitals, "
                       "frequent welfare checks on elderly and isolated people.",
            "SEVERE": "Treat as emergency-level heat stress: stop outdoor work in peak hours, activate heat action plan fully."}
    return dict(
        CURRENT_THERMAL_RISK=f"WBGT band: {band}",
        HISTORICAL_ANALOGUE=top.assign(date=pd.to_datetime(top["date"]).dt.strftime("%Y-%m-%d"))[["date", "state", "similarity_score", "maximum_temperature_c", "relative_humidity_percent",
                                 "wbgt_c", "heat_related_deaths_total"]],
        EXPECTED_HEALTH_IMPACT=(f"Historical SYNTHETIC scenarios with similar thermal conditions were associated with an average of "
                                f"{top.heat_related_deaths_total.mean():.2f} simulated heat-related deaths/day (5 closest days) and "
                                f"{stable.heat_related_deaths_total.mean():.2f} (25 closest). This is a model-estimated heat-related "
                                f"mortality burden for decision support, not a forecast for any individual or day."),
        VULNERABLE_POPULATIONS=(f"Among the 25 closest analogues: deaths under 30 / 30-59 / 60+ = {int(ages.iloc[0])} / {int(ages.iloc[1])} / "
                                f"{int(ages.iloc[2])}; male / female = {int(sx.iloc[0])} / {int(sx.iloc[1])} (simulated; small counts, noisy)."),
        RECOMMENDED_PRECAUTIONS=prec.get(band, "Follow local heat action plan guidance."),
        features_used=keys)

# ---------------------------------------------------------------- reporting helpers
def md_table(df, index=True, nd=2):
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    L = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in d.iterrows():
        L.append("| " + " | ".join(f"{v:.{nd}f}" if isinstance(v, (float, np.floating)) else str(v) for v in r.values) + " |")
    return "\n".join(L)

def spearman(a, b): return a.rank().corr(b.rank())

# ---------------------------------------------------------------- data dictionary
SPEC = {
 "date": ("date", "YYYY-MM-DD", "Calendar date of the record.", "Consecutive dates ending the day before generation date."),
 "state": ("string", "-", "State the record describes (state-level aggregate).", "Fixed set of 3 states."),
 "data_type": ("string", "-", "Honesty flag; always SYNTHETIC.", "Constant."),
 "population": ("int", "persons", "State population used as denominator.", "Synthetic demographic assumption (rounded 2026 projection-style figure, not official)."),
 "elderly_population_percent": ("float", "%", "Share aged 60+.", "Synthetic demographic assumption (historical baseline was lower; Census-2011-era values roughly 9-13%, verify before citing)."),
 "working_age_population_percent": ("float", "%", "Share aged 30-59 (the paper's mid-age bucket, not the 15-59 convention).", "Synthetic demographic assumption; chosen so under-30 + 30-59 + 60+ = 100."),
 "under_30_population_percent": ("float", "%", "Share aged under 30.", "Synthetic demographic assumption."),
 "outdoor_worker_fraction": ("float", "0-1", "Fraction of workers with substantial outdoor work.", "Synthetic assumption; not an official statistic."),
 "urban_population_percent": ("float", "%", "Urban share of population.", "Synthetic demographic assumption."),
 "maximum_temperature_c": ("float", "deg C", "State-representative daily maximum air temperature.", "Sinusoidal climatology + monsoon/winter dips + AR(1) anomaly + random heat episodes; state parameters."),
 "minimum_temperature_c": ("float", "deg C", "Background daily minimum temperature.", "Tmax minus diurnal range (humidity/season dependent)."),
 "mean_temperature_c": ("float", "deg C", "Daily mean temperature.", "(Tmax+Tmin)/2."),
 "relative_humidity_percent": ("float", "%", "Daily mean relative humidity.", "Climatology (dry season dip, monsoon rise) + AR(1) noise, negatively coupled to Tmax anomaly."),
 "wind_speed_mps": ("float", "m/s", "Daily mean wind speed.", "Gamma draw scaled by monsoon factor."),
 "dew_point_c": ("float", "deg C", "Dew point.", "Magnus formula from mean temperature and mean RH."),
 "heat_index_c": ("float", "deg C", "Heat index at daily Tmax and 15:00 RH, converted to Celsius.", "NWS Rothfusz regression (computed in deg F then converted)."),
 "heat_index_f": ("float", "deg F", "Same heat index in Fahrenheit (explicit unit, distinct from WBGT).", "NWS Rothfusz regression."),
 "wbgt_c": ("float", "deg C", "Daily peak (hourly max) outdoor WBGT.", "0.7*Stull wet-bulb + 0.2*globe + 0.1*air; globe = air + simple solar increment reduced by wind and cloud. An approximation, not a measured WBGT."),
 "wbgt_category": ("string", "-", "LOW <28, CAUTION 28-30, DANGER 30-32, EXTREME 32-35, SEVERE >35 (WBGT deg C).", "Project thermal-risk bands applied to wbgt_c."),
 "hours_above_heat_threshold": ("int", "hours", "Hours per day with air temperature >= 35 C.", "Cosine diurnal curve, peak 15:00."),
 "nighttime_min_temperature_c": ("float", "deg C", "Night minimum including an urban-heat-island offset (up to 1.5 C).", "Tmin + 1.5*urban_heat_index."),
 "heatwave_day": ("bool", "-", "Heatwave flag.", "IMD-INSPIRED, state-level synthetic rule: Tmax >= state threshold (TN 37.5, KA 36.5, KL 35.0) AND anomaly >= 2.0 C (KL 1.8 C). Not the official IMD definition."),
 "consecutive_hot_days": ("int", "days", "Run length of days with Tmax >= state hot threshold (TN 36.5, KA 35.5, KL 33.5).", "Run-length count (temperature-based)."),
 "temperature_anomaly_c": ("float", "deg C", "Tmax minus the state's smooth climatological Tmax for that day of year.", "Difference from the generating climatology."),
 "humidity_anomaly_percent": ("float", "% points", "RH minus climatological RH.", "Difference from the generating climatology."),
 "heat_duration_hours": ("int", "hours", "Hours per day with hourly WBGT >= 30 C (DANGER band or above).", "Hourly WBGT from the thermal chain."),
 "consecutive_heat_days": ("int", "days", "Run length of days with daily peak WBGT >= 30 C (thermal-stress-based, unlike consecutive_hot_days).", "Run-length count."),
 "nighttime_heat_stress": ("float", "0-1", "Night heat load.", "clip((nighttime_min_temperature_c - 24)/6, 0, 1)."),
 "humidity_burden": ("float", "0-1", "Moisture load on cooling by sweating.", "clip((dew_point_c - 18)/8, 0, 1)."),
 "outdoor_exposure_index": ("float", "0-1", "Effective outdoor exposure.", "outdoor_worker_fraction/0.6 x weekday factor (Sun 0.78, Sat 0.92) x monsoon reduction + noise."),
 "urban_heat_index": ("float", "0-1", "Urban heat amplification proxy (a synthetic index, not the meteorological heat index).", "0.8*urban share + 0.12*clip((Tmax-32)/8,0,1) + noise."),
 "population_exposure_index": ("float", "0-1", "Population at risk of exposure.", "0.5*population/max population + 0.3*urban share + 0.2*outdoor_exposure_index."),
 "vulnerability_index": ("float", "0-1", "Population vulnerability.", "0.35*elderly/20 + 0.25*outdoor/0.6 + 0.25*(1-healthcare) + 0.15*(1-cooling) + slow AR(1) drift."),
 "public_health_response_index": ("float", "0-1", "Synthetic response readiness.", "State base + 0.15 if a heatwave day occurred in last 3 days + noise."),
 "healthcare_access_index": ("float", "0-1", "Synthetic healthcare access.", "State base + slow drift. Not an official indicator."),
 "heat_action_plan_index": ("float", "0-1", "Synthetic heat-action-plan strength.", "Constant state assumption. Not an official indicator."),
 "cooling_access_index": ("float", "0-1", "Synthetic access to cooling.", "State base + slow drift. Not an official indicator."),
 "heat_exposure_index": ("float", "index >=0", "Same-day thermal hazard score X_t (drives mortality).", "0.5*piecewise-linear(Tmax) + 0.5*piecewise-linear(WBGT); slopes steepen with heat."),
 "heat_exposure_lag_1": ("float", "index", "X_t at t-1.", "Lag of heat_exposure_index."),
 "heat_exposure_lag_2": ("float", "index", "X_t at t-2.", "Lag."),
 "heat_exposure_lag_3": ("float", "index", "X_t at t-3.", "Lag."),
 "heat_exposure_lag_7": ("float", "index", "X_t at t-7.", "Lag."),
 "cumulative_heat_load_3day": ("float", "index", "Sum of X over t-2..t.", "Rolling sum."),
 "cumulative_heat_load_7day": ("float", "index", "Sum of X over t-6..t.", "Rolling sum."),
 "expected_heatstroke_deaths": ("float", "deaths/day", "Model expectation (mean) for heatstroke deaths.", "state base x exp(eta_heatstroke)."),
 "expected_other_heat_related_deaths": ("float", "deaths/day", "Model expectation for other heat-exacerbated deaths.", "state base x exp(eta_other)."),
 "expected_heat_related_deaths": ("float", "deaths/day", "Model expectation, total. NOT an observation.", "Sum of the two expectations."),
 "heatstroke_deaths": ("int", "deaths", "Simulated heatstroke deaths.", "Negative Binomial draw around expectation x lognormal shock."),
 "other_heat_related_deaths": ("int", "deaths", "Simulated heat-exacerbated deaths from other causes (cardiovascular, renal, respiratory etc.).", "Negative Binomial draw; ratio to heatstroke is an ASSUMPTION (paper does not measure it)."),
 "heat_related_deaths_total": ("int", "deaths", "heatstroke_deaths + other_heat_related_deaths (stochastic realization).", "Sum."),
 "heat_related_deaths_male": ("int", "deaths", "Male share of total.", "Dirichlet-perturbed multinomial over 6 sex-age cells (both components)."),
 "heat_related_deaths_female": ("int", "deaths", "Female share of total.", "Same."),
 "heatstroke_deaths_male": ("int", "deaths", "Male heatstroke deaths.", "Multinomial cells calibrated to paper Table 1 shares."),
 "heatstroke_deaths_female": ("int", "deaths", "Female heatstroke deaths.", "Same."),
 "heat_related_deaths_under_30": ("int", "deaths", "Deaths aged <30 (naming follows the MORTALITY VARIABLES list; equals 'deaths_under_30' in the example record).", "Multinomial cells."),
 "heat_related_deaths_30_59": ("int", "deaths", "Deaths aged 30-59.", "Multinomial cells."),
 "heat_related_deaths_60_plus": ("int", "deaths", "Deaths aged 60+.", "Multinomial cells."),
 "mortality_anomaly": ("float", "deaths", "Observed minus expected total.", "heat_related_deaths_total - expected_heat_related_deaths."),
 "heat_related_mortality_rate_per_100000": ("float", "per 100,000 (daily)", "Primary rate. NOT all-cause mortality.", "total / population x 100000."),
 "heatstroke_mortality_rate_per_100000": ("float", "per 100,000 (daily)", "Heatstroke-only daily rate.", "heatstroke / population x 100000."),
 "thermal_signature": ("json string", "-", "Multi-dimensional signature for analogue search: max temp, mean temp, humidity, WBGT, heat index (C), heat duration, consecutive heat days.", "Bundle of existing columns."),
}
DEFAULT_LIMIT = "Synthetic; state-level aggregate (no district resolution); values are model outputs, not observations."

def write_dictionary(path, cols):
    L = ["# Data dictionary - `mortality_synthetic_daily.csv`", "",
         "**ALL DATA ARE SYNTHETIC (`data_type = SYNTHETIC`).** Not NCRB, not IMD, not official, not real 2025/2026 mortality. "
         "Paper: Guin, Bhan & Sethi (2025), *Temperature* 12(2):179-199 is used only as a statistical calibration reference.", "",
         "Every column is *synthetic* (real/synthetic = SYNTHETIC). Source/reference column says what calibrates or motivates it.", "",
         "| column_name | data_type | unit | meaning | generation_method | source/reference | real/synthetic | limitations |",
         "|---|---|---|---|---|---|---|---|"]
    for c in cols:
        dtp, unit, mean, meth = SPEC[c]
        if c.startswith(("expected", "heatstroke", "other_heat", "heat_related", "mortality")) or c in ("heatstroke_deaths",):
            src = "Model structure and sex/age shares calibrated to Guin et al. 2025 (Tables 1, 4, 6, 7); everything else assumption"
        elif c in ("date", "state", "data_type"):
            src = "n/a"
        elif c.endswith("_index") or "lag" in c or "cumulative" in c:
            src = "Project assumption (synthetic index)"
        else:
            src = "Modelling assumption (synthetic)"
        L.append(f"| {c} | {dtp} | {unit} | {mean} | {meth} | {src} | SYNTHETIC | {DEFAULT_LIMIT} |")
    L += ["", "## Notes", "- Temperatures in deg C. Heat index is given in both C and F; WBGT is always deg C and is NOT a Fahrenheit heat index.",
          "- Death counts are tiny integers per day per state; use aggregates (weeks/season) for analysis.",
          "- Naming: the age columns follow the MORTALITY VARIABLES list (`heat_related_deaths_under_30` etc.), not the shorter `deaths_under_30` in the example record.",
          "- Demographic percentages are synthetic assumptions, not current official statistics."]
    Path(path).write_text("\n".join(L), encoding="utf-8")

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generation-date", default=None, help="YYYY-MM-DD (default today)")
    ap.add_argument("--start-date", default=None); ap.add_argument("--end-date", default=None)
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=".")
    ap.add_argument("--sensitivity-target", type=float, default=PAPER_REL_SENS)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); (out / "charts").mkdir(exist_ok=True)
    gen = dt.date.fromisoformat(a.generation_date) if a.generation_date else dt.date.today()
    end = dt.date.fromisoformat(a.end_date) if a.end_date else gen - dt.timedelta(days=1)
    start = dt.date.fromisoformat(a.start_date) if a.start_date else end - dt.timedelta(days=a.days - 1)
    dates_all = pd.date_range(start - dt.timedelta(days=WARMUP), end)
    dates = dates_all[WARMUP:]
    ss = np.random.SeedSequence(a.seed); kids = ss.spawn(len(STATES) * 2)
    W, DR_full, CTX_full, DR0, DR1, CTX = {}, {}, {}, {}, {}, {}
    amj = np.isin(dates_all.month, [4, 5, 6])
    for i, s in enumerate(STATES):
        rng = np.random.default_rng(kids[i]); p = PROFILES[s]
        W[s] = gen_weather(s, dates_all, rng)
        uhi = uhi_from(W[s]["tmax"], W[s], p)
        DR_full[s] = compute_drivers(W[s], uhi)
        CTX_full[s] = compute_context(s, dates_all, W[s], DR_full[s], uhi)
        DR0[s] = cut(DR_full[s]); CTX[s] = cut(CTX_full[s])
        DR1[s] = cut(compute_drivers(W[s], uhi, amj, 1.0))

    # ---- calibration: relative response of annual expected heatstroke deaths to +1C on Apr-Jun Tmax
    def R_of(beta):
        Rs = [mu_raw(DR1[s], CTX[s], beta, "heat").sum() / mu_raw(DR0[s], CTX[s], beta, "heat").sum() - 1 for s in STATES]
        return float(np.mean(Rs)), Rs
    lo, hi = 0.01, 6.0
    assert R_of(hi)[0] > a.sensitivity_target, "target sensitivity unreachable"
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        if R_of(mid)[0] < a.sensitivity_target: lo = mid
        else: hi = mid
    beta = math.sqrt(lo * hi); R_mean, R_states = R_of(beta)

    # ---- simulate
    rows, hs_cells_all, base = [], {}, {}
    for i, s in enumerate(STATES):
        rng = np.random.default_rng(kids[len(STATES) + i]); p = PROFILES[s]; dr = DR0[s]; ctx = CTX[s]; n = len(dates)
        rh_raw = mu_raw(dr, ctx, beta, "heat"); ro_raw = mu_raw(dr, ctx, beta, "other")
        bh = p["target_heatstroke"] / rh_raw.sum(); bo = CFG["other_to_heatstroke_ratio"] * p["target_heatstroke"] / ro_raw.sum()
        base[s] = dict(heatstroke=bh, other=bo)
        e_h, e_o = bh * rh_raw, bo * ro_raw
        y = {}
        for kind, e in (("heat", e_h), ("other", e_o)):
            c = CFG[kind]
            z = ar1(rng, n, CFG["shock_phi"], 1.0); shock = np.exp(c["shock_sd"] * z - c["shock_sd"] ** 2 / 2)
            mu = e * shock; r = c["nb_size"]
            y[kind] = rng.negative_binomial(r, r / (r + mu))
        tilt = np.array([1, 1, 1, 1, p["elderly"] / 12, p["elderly"] / 12])
        bp_h = PAPER_CELL_MEANS / PAPER_CELL_MEANS.sum() * tilt
        bp_o = np.array(CFG["other_cell_base"]) * tilt
        adj = cell_adjust(ctx, dr)
        ch_ = split_cells(rng, y["heat"], bp_h / bp_h.sum(), adj, CFG["heat"]["kappa"])
        co_ = split_cells(rng, y["other"], bp_o / bp_o.sum(), adj, CFG["other"]["kappa"])
        ct = ch_ + co_; hs_cells_all[s] = ch_
        tot = y["heat"] + y["other"]; exp_t = e_h + e_o; pop = p["population"]
        sig = [json.dumps(dict(max_temperature_c=round(float(a1), 2), mean_temperature_c=round(float(a2), 2),
                               humidity_percent=round(float(a3), 1), wbgt_c=round(float(a4), 2),
                               heat_index_c=round(float(a5), 2), heat_duration_hours=int(a6), consecutive_heat_days=int(a7)))
               for a1, a2, a3, a4, a5, a6, a7 in zip(dr["tmax"], dr["tmean"], W[s]["rh"][WARMUP:], dr["wbgt"], dr["hi_c"],
                                                     dr["dur"], ctx["consec_heat"])]
        rows.append(pd.DataFrame(dict(
            date=dates.strftime("%Y-%m-%d"), state=s, data_type="SYNTHETIC", population=pop,
            elderly_population_percent=p["elderly"], working_age_population_percent=p["wa"], under_30_population_percent=p["u30"],
            outdoor_worker_fraction=p["outdoor"], urban_population_percent=p["urban"],
            maximum_temperature_c=dr["tmax"].round(2), minimum_temperature_c=dr["tmin"].round(2), mean_temperature_c=dr["tmean"].round(2),
            relative_humidity_percent=W[s]["rh"][WARMUP:].round(1), wind_speed_mps=W[s]["wind"][WARMUP:].round(2),
            dew_point_c=dr["td"].round(2), heat_index_c=dr["hi_c"].round(2), heat_index_f=dr["hi_f"].round(2),
            wbgt_c=dr["wbgt"].round(2), wbgt_category=wbgt_category(dr["wbgt"]), hours_above_heat_threshold=dr["hrs35"],
            nighttime_min_temperature_c=dr["night_min"].round(2), heatwave_day=ctx["hw"], consecutive_hot_days=ctx["consec_hot"],
            temperature_anomaly_c=ctx["anom"].round(2), humidity_anomaly_percent=ctx["hum_anom"].round(1),
            heat_duration_hours=dr["dur"], consecutive_heat_days=ctx["consec_heat"],
            nighttime_heat_stress=dr["night"].round(3), humidity_burden=dr["hum"].round(3),
            outdoor_exposure_index=ctx["out"].round(3), urban_heat_index=ctx["uhi"].round(3),
            population_exposure_index=ctx["popexp"].round(3), vulnerability_index=ctx["vul"].round(3),
            public_health_response_index=ctx["phr"].round(3), healthcare_access_index=ctx["hc"].round(3),
            heat_action_plan_index=ctx["hap"].round(3), cooling_access_index=ctx["cool"].round(3),
            heat_exposure_index=dr["X"].round(4), heat_exposure_lag_1=dr["X1"].round(4), heat_exposure_lag_2=dr["X2"].round(4),
            heat_exposure_lag_3=dr["X3"].round(4), heat_exposure_lag_7=dr["X7"].round(4),
            cumulative_heat_load_3day=dr["cum3"].round(4), cumulative_heat_load_7day=dr["cum7"].round(4),
            expected_heatstroke_deaths=e_h.round(5), expected_other_heat_related_deaths=e_o.round(5),
            expected_heat_related_deaths=exp_t.round(5),
            heatstroke_deaths=y["heat"], other_heat_related_deaths=y["other"], heat_related_deaths_total=tot,
            heat_related_deaths_male=ct[:, [0, 2, 4]].sum(1), heat_related_deaths_female=ct[:, [1, 3, 5]].sum(1),
            heatstroke_deaths_male=ch_[:, [0, 2, 4]].sum(1), heatstroke_deaths_female=ch_[:, [1, 3, 5]].sum(1),
            heat_related_deaths_under_30=ct[:, [0, 1]].sum(1), heat_related_deaths_30_59=ct[:, [2, 3]].sum(1),
            heat_related_deaths_60_plus=ct[:, [4, 5]].sum(1),
            mortality_anomaly=(tot - exp_t).round(5),
            heat_related_mortality_rate_per_100000=(tot / pop * 1e5).round(6),
            heatstroke_mortality_rate_per_100000=(y["heat"] / pop * 1e5).round(6),
            thermal_signature=sig)))
    df = pd.concat(rows, ignore_index=True)
    df["_o"] = df.state.map({s: i for i, s in enumerate(STATES)})
    df = df.sort_values(["date", "_o"]).drop(columns="_o").reset_index(drop=True)
    cols = list(SPEC.keys()); df = df[cols]

    # ---- integrity checks
    assert len(df) == len(dates) * 3 and (df.data_type == "SYNTHETIC").all()
    assert (df.heat_related_deaths_total == df.heatstroke_deaths + df.other_heat_related_deaths).all()
    assert (df.heat_related_deaths_total == df.heat_related_deaths_male + df.heat_related_deaths_female).all()
    assert (df.heat_related_deaths_total == df.heat_related_deaths_under_30 + df.heat_related_deaths_30_59 + df.heat_related_deaths_60_plus).all()

    df.to_csv(out / "mortality_synthetic_daily.csv", index=False)
    recs = json.loads(df.to_json(orient="records"))
    for r in recs: r["thermal_signature"] = json.loads(r["thermal_signature"])
    meta = dict(data_type="SYNTHETIC", warning="Synthetic prototype data. NOT NCRB/IMD/official/real mortality data. Not a forecast.",
                reference="Guin P, Bhan N, Sethi K (2025) Temperature 12(2):179-199 (calibration reference only)",
                date_range=[str(dates[0].date()), str(dates[-1].date())], rows=len(df), random_seed=a.seed)
    (out / "mortality_synthetic_daily.json").write_text(json.dumps(dict(metadata=meta, records=recs), indent=1), encoding="utf-8")
    write_dictionary(out / "mortality_data_dictionary.md", cols)

    # ---- parameters
    params = dict(
        data_type="SYNTHETIC", random_seed=a.seed, generation_date=str(gen), date_range=meta["date_range"], warmup_days=WARMUP,
        model="Negative Binomial counts (mean = base x exp(eta) x lognormal AR(1) shock); heatstroke + other components; multinomial sex-age split with Dirichlet noise",
        temperature_effect=dict(value=beta, origin="CALIBRATED", note="beta on lag-weighted heat exposure; solved so mean relative rise in annual expected heatstroke deaths for +1C on Apr-Jun Tmax equals the paper-implied ratio 8.028/39"),
        calibration=dict(target_relative_increase_per_C=a.sensitivity_target, achieved_mean=R_mean,
                         achieved_by_state=dict(zip(STATES, R_states)), origin="paper coefficient 8.028 (Table 4) / mean 39 (Table 1)"),
        hazard_temperature_segments=dict(value=CFG["hazard_T_segments"], origin="ASSUMPTION (convex piecewise; paper motivates thresholds at 33 and 38 C)"),
        hazard_wbgt_segments=dict(value=CFG["hazard_W_segments"], origin="ASSUMPTION"),
        wbgt_weight_in_exposure=CFG["wbgt_weight"], seasonality_strength=dict(value=CFG["seasonality_strength"], origin="ASSUMPTION"),
        humidity_effect=dict(heatstroke=CFG["heat"]["hum"], other=CFG["other"]["hum"], origin="ASSUMPTION"),
        duration_effect_per_hour=dict(heatstroke=CFG["heat"]["dur"], other=CFG["other"]["dur"], origin="ASSUMPTION"),
        night_effect=dict(heatstroke=CFG["heat"]["night"], other=CFG["other"]["night"], origin="ASSUMPTION"),
        lag_effect=dict(weights_lag_0_1_2_3_7=dict(heatstroke=CFG["heat"]["lag_w"], other=CFG["other"]["lag_w"]), origin="ASSUMPTION"),
        vulnerability_effect=dict(heatstroke=CFG["heat"]["vul"], other=CFG["other"]["vul"], origin="ASSUMPTION"),
        outdoor_effect=dict(heatstroke=CFG["heat"]["out"], other=CFG["other"]["out"], origin="ASSUMPTION"),
        health_response_effects=dict(public_health_response=CFG["heat"]["phr"], cooling_access=CFG["heat"]["cool"],
                                     origin="ASSUMPTION; direction supported by paper's negative health-spend/urban coefficients (not significant for totals)"),
        dispersion_parameter=dict(heatstroke_nb_size=CFG["heat"]["nb_size"], other_nb_size=CFG["other"]["nb_size"], origin="ASSUMPTION"),
        shock=dict(sd_heatstroke=CFG["heat"]["shock_sd"], sd_other=CFG["other"]["shock_sd"], ar1_phi=CFG["shock_phi"], origin="ASSUMPTION"),
        other_to_heatstroke_ratio=dict(value=CFG["other_to_heatstroke_ratio"], origin="ASSUMPTION (paper covers heatstroke only)"),
        sex_age_shares_heatstroke=dict(cells=CELLS, paper_table1_means=PAPER_CELL_MEANS.tolist(), origin="PAPER (Table 1)"),
        sex_age_shares_other=dict(value=CFG["other_cell_base"], origin="ASSUMPTION (older, more balanced by sex)"),
        dirichlet_kappa=dict(heatstroke=CFG["heat"]["kappa"], other=CFG["other"]["kappa"]),
        state_baseline=dict({s: dict(annual_heatstroke_target=PROFILES[s]["target_heatstroke"], calibrated_base_daily_scale=base[s],
                                     paper_cumulative_2001_2014=PAPER_CUM[s], paper_mean_per_year=PAPER_CUM[s] / 14,
                                     origin="target = ASSUMPTION anchored on (not equal to) paper values") for s in STATES}),
        state_profiles={s: {k: v for k, v in PROFILES[s].items()} for s in STATES},
        similarity=dict(features=list(SIG_COLS), weights=SIG_W, standardisation="divide by dataset SD", score="100*exp(-weighted RMS z-distance)"),
        paper_reference_values=dict(mean_total=39, sd_total=53.9, min=0, max=418, mean_male=31, mean_female=8, coef_asmt_total=8.028,
                                    table7_asmt2_total=21.50, table6_smt_c=7.911, table6_smt_c_sq=0.798))
    (out / "mortality_model_parameters.json").write_text(json.dumps(params, indent=2, default=float), encoding="utf-8")

    # ---- validation
    d = df.copy(); d["date"] = pd.to_datetime(d["date"]); d["month"] = d.date.dt.to_period("M").astype(str)
    T = "heat_related_deaths_total"
    st = d.groupby("state").agg(population=("population", "first"), days=("date", "count"), heatstroke=("heatstroke_deaths", "sum"),
                                other=("other_heat_related_deaths", "sum"), total=(T, "sum"), expected=("expected_heat_related_deaths", "sum"),
                                max_daily=(T, "max"), mean_tmax=("maximum_temperature_c", "mean"), max_tmax=("maximum_temperature_c", "max"),
                                mean_wbgt=("wbgt_c", "mean"), max_wbgt=("wbgt_c", "max"), heatwave_days=("heatwave_day", "sum"))
    st["rate_per_100k_year"] = st.total / st.population * 1e5
    monthly = d.pivot_table(index="month", columns="state", values=T, aggfunc="sum")[STATES]
    dist = d.groupby("state")[["maximum_temperature_c", "wbgt_c", "relative_humidity_percent"]].describe().T.round(2)
    cat = d.groupby("wbgt_category").agg(days=("date", "count"), mean_deaths_per_day=(T, "mean"), total_deaths=(T, "sum"),
                                         mean_expected=("expected_heat_related_deaths", "mean"))
    cat = cat.reindex([c for c in ["LOW", "CAUTION", "DANGER", "EXTREME", "SEVERE"] if c in cat.index]); cat["share_of_deaths_pct"] = 100 * cat.total_deaths / cat.total_deaths.sum()
    hw = d.groupby(["state", "heatwave_day"]).agg(days=("date", "count"), mean_deaths_per_day=(T, "mean"), total=(T, "sum")).reset_index()
    hwp = d.groupby("heatwave_day").agg(days=("date", "count"), mean_deaths_per_day=(T, "mean"), total=(T, "sum"))
    bins = [0, 30, 32, 34, 36, 38, 40, 50]
    d["tbin"] = pd.cut(d.maximum_temperature_c, bins).astype(str)
    tb = d.groupby("tbin", observed=True).agg(days=("date", "count"), mean_deaths_per_day=(T, "mean"), mean_expected=("expected_heat_related_deaths", "mean"))
    tb = tb.loc[sorted(tb.index, key=lambda x: float(x.split(",")[0][1:]))]
    d["wbin"] = pd.cut(d.wbgt_c, [0, 26, 28, 30, 32, 35, 50]).astype(str)
    wb = d.groupby("wbin", observed=True).agg(days=("date", "count"), mean_deaths_per_day=(T, "mean"))
    wb = wb.loc[sorted(wb.index, key=lambda x: float(x.split(",")[0][1:]))]
    mf = df.heat_related_deaths_male.sum() / df.heat_related_deaths_female.sum()
    hmf = df.heatstroke_deaths_male.sum() / df.heatstroke_deaths_female.sum()
    ageT = df[["heat_related_deaths_under_30", "heat_related_deaths_30_59", "heat_related_deaths_60_plus"]].sum()
    hc = sum(hs_cells_all[s].sum(0) for s in STATES); hc_sh = hc / hc.sum()
    pap_sh = PAPER_CELL_MEANS / PAPER_CELL_MEANS.sum()
    cv = ["maximum_temperature_c", "heat_index_c", "wbgt_c", "cumulative_heat_load_7day", "consecutive_hot_days", "relative_humidity_percent", T, "expected_heat_related_deaths"]
    cm = d[cv].corr().round(3)
    sp = pd.DataFrame({"Pearson": [d[c].corr(d[T]) for c in cv[:-2]], "Spearman": [spearman(d[c], d[T]) for c in cv[:-2]]}, index=cv[:-2]).round(3)
    spst = pd.DataFrame({s: [d[d.state == s][c].corr(d[d.state == s][T]) for c in cv[:3]] for s in STATES}, index=cv[:3]).round(3)
    lagr = []
    for k in range(0, 11):
        sh = d.groupby("state")["maximum_temperature_c"].shift(k); m = sh.notna()
        shw = d.groupby("state")["wbgt_c"].shift(k)
        lagr.append((k, d.loc[m, T].corr(sh[m]), d.loc[m, T].corr(shw[m])))
    lagdf = pd.DataFrame(lagr, columns=["lag_days", "corr_deaths_vs_Tmax_lag", "corr_deaths_vs_WBGT_lag"]).set_index("lag_days").round(3)
    lagx = pd.DataFrame({"corr_with_deaths": [d[c].corr(d[T]) for c in ["heat_exposure_index", "heat_exposure_lag_1", "heat_exposure_lag_2", "heat_exposure_lag_3", "heat_exposure_lag_7", "cumulative_heat_load_3day", "cumulative_heat_load_7day"]]},
                        index=["heat_exposure_index", "lag_1", "lag_2", "lag_3", "lag_7", "cum_3day", "cum_7day"]).round(3)
    pap = pd.DataFrame({
        "paper (NCRB heatstroke, 2001-14)": [f"{PAPER_CUM[s]/14:.1f}/yr" for s in STATES],
        "synthetic heatstroke (365 d)": [int(st.loc[s, "heatstroke"]) for s in STATES],
        "synthetic total heat-related": [int(st.loc[s, "total"]) for s in STATES]}, index=STATES)
    q = dict(max_temperature_c=38.1, wbgt_c=32.5, humidity_percent=64.0, consecutive_heat_days=3, heat_duration_hours=None)
    ana = analyse_scenario(d, q)

    # ---- charts
    fig, ax = plt.subplots(figsize=(9, 4)); monthly.plot(kind="bar", ax=ax); ax.set_ylabel("simulated heat-related deaths"); ax.set_title("SYNTHETIC: monthly heat-related deaths"); plt.tight_layout(); fig.savefig(out / "charts/monthly_deaths.png", dpi=110); plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4)); tb.mean_deaths_per_day.plot(kind="bar", ax=axs[0], color="tab:red"); axs[0].set_title("Mean deaths/day by Tmax bin (C)"); wb.mean_deaths_per_day.plot(kind="bar", ax=axs[1], color="tab:orange"); axs[1].set_title("Mean deaths/day by WBGT bin (C)"); plt.tight_layout(); fig.savefig(out / "charts/deaths_by_temperature_wbgt.png", dpi=110); plt.close(fig)
    t = d[d.state == "Tamil Nadu"]
    fig, axs = plt.subplots(3, 1, figsize=(10, 7), sharex=True); axs[0].plot(t.date, t.maximum_temperature_c); axs[0].set_ylabel("Tmax C"); axs[1].plot(t.date, t.wbgt_c, color="tab:orange"); axs[1].axhline(30, ls="--", c="grey"); axs[1].set_ylabel("WBGT C"); axs[2].bar(t.date, t[T], color="tab:red", width=1.0); axs[2].plot(t.date, t.expected_heat_related_deaths, c="k", lw=1); axs[2].set_ylabel("deaths (bars) / expected (line)"); axs[0].set_title("SYNTHETIC - Tamil Nadu"); plt.tight_layout(); fig.savefig(out / "charts/tamil_nadu_timeseries.png", dpi=110); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 3.5)); lagdf.plot(kind="bar", ax=ax); ax.set_title("Correlation of deaths with lagged Tmax / WBGT"); plt.tight_layout(); fig.savefig(out / "charts/lag_correlation.png", dpi=110); plt.close(fig)

    # ---- report
    rep = f"""# Validation report - synthetic heat-related mortality dataset

**DATA HONESTY: every record is SYNTHETIC (`data_type = SYNTHETIC`). This is NOT NCRB, IMD, official or real 2025/2026 mortality data. Correlations below describe a simulation, not causal epidemiology, and nothing here is a mortality forecast.**

Reference paper (calibration only): Guin, Bhan & Sethi (2025), *Temperature* 12(2):179-199. Seed {a.seed}; window {meta['date_range'][0]} to {meta['date_range'][1]}.

## 1. Dataset dimensions
{len(df)} rows x {df.shape[1]} columns; {len(dates)} days x 3 states. Integrity checks passed: total = heatstroke + other; male+female = total; age groups sum to total; all rows SYNTHETIC.

## 2. State-wise summary
{md_table(st)}

## 3. Monthly distribution of simulated deaths
{md_table(monthly, nd=0)}

![monthly](charts/monthly_deaths.png)

## 4-5. Temperature, WBGT and humidity distributions
{md_table(dist, nd=2)}

WBGT category breakdown (all states):

{md_table(cat)}

## 6-7. Heatwave vs non-heatwave days
{md_table(hwp)}

By state:

{md_table(hw, index=False)}

## 8. Male / female
Total heat-related: male:female = {mf:.2f}. Heatstroke only: {hmf:.2f} (paper: 31/8 = 3.9 state-year means; 3-5x nationally, Fig. 1c).

## 9. Age distribution
Total heat-related: <30 = {ageT.iloc[0]/ageT.sum()*100:.1f}%, 30-59 = {ageT.iloc[1]/ageT.sum()*100:.1f}%, 60+ = {ageT.iloc[2]/ageT.sum()*100:.1f}%.
Heatstroke component only (compare with paper Table 1 means): <30 = {(hc_sh[0]+hc_sh[1])*100:.1f}% (paper {(pap_sh[0]+pap_sh[1])*100:.1f}%), 30-59 = {(hc_sh[2]+hc_sh[3])*100:.1f}% (paper {(pap_sh[2]+pap_sh[3])*100:.1f}%), 60+ = {(hc_sh[4]+hc_sh[5])*100:.1f}% (paper {(pap_sh[4]+pap_sh[5])*100:.1f}%). Shares are tilted by each state's synthetic elderly share, and only ~{int(hc.sum())} heatstroke deaths were simulated, so shares are noisy and exact agreement is not expected.

## 10. Correlation matrix (Pearson, pooled)
{md_table(cm, nd=3)}

Deaths vs drivers, Pearson and Spearman (pooled):

{md_table(sp, nd=3)}

Pearson by state (deaths vs Tmax / heat index / WBGT):

{md_table(spst, nd=3)}

Correlation is not causation; the simulation only encodes the relationships written into the generator. Daily counts are small, so daily correlations are modest by design.

## 11-12. Temperature and WBGT relationships
{md_table(tb)}

{md_table(wb)}

![bins](charts/deaths_by_temperature_wbgt.png)
![tn](charts/tamil_nadu_timeseries.png)

The relationship is convex but noisy: some hot days have zero deaths and some moderate days have several.

## 13. Lag relationship
{md_table(lagdf, nd=3)}

{md_table(lagx, nd=3)}

![lag](charts/lag_correlation.png)

## 14. Comparison with the paper
{md_table(pap)}

- Ordering TN > KA > KL matches the paper (228 > 97 > 10 cumulative). Synthetic annual heatstroke targets (TN 24, KA 12, KL 5) are ASSUMPTIONS anchored on, not equal to, the paper: they are above the paper's per-year averages (TN 16.3, KA 6.9, KL 0.7) because NCRB counts are police-recorded and likely undercounted, and Kerala was deliberately not set to near-zero because of humidity-driven stress.
- Paper sensitivity: +8.028 deaths per +1C average summer max, mean 39 deaths/state-year, i.e. +{PAPER_REL_SENS*100:.1f}%. Simulated: +1C on all Apr-Jun Tmax raises annual expected heatstroke deaths by {R_mean*100:.1f}% on average (TN {R_states[0]*100:.1f}%, KL {R_states[1]*100:.1f}%, KA {R_states[2]*100:.1f}%). The mean is calibrated to the target; the state split is an outcome of the model.
- Sex ratio and age shares: see sections 8-9 (heatstroke component approximates the paper's Table 1 cell means).
- Threshold shape: the paper's spline (Table 7) finds the largest per-degree effect in the 33-38C bin and an insignificant/negative effect above 38C (total deaths -8.96, SE 8.29), which the authors attribute to adaptation. The requested design instead makes extreme heat the steepest part. The quadratic model (Table 6, positive squared term 0.798, significant) supports convexity, but this is a **known divergence** from the piecewise result. The paper's data are annual state means, so a daily curve cannot be identified from it.
- Not comparable: the paper's mean of 39 is per state-year over 24 states; the max 418 and SD 53.9 are not reproduced (3 small states only).

## 15. Limitations
State-level only (no districts); weather is simulated, not IMD data; WBGT is an approximation; heatwave rule is IMD-inspired, not official; the 3:1 ratio of other heat-related deaths to heatstroke is an assumption; demographic values are assumptions; daily counts are very small; annual totals are calibrated to assumed targets; NCRB heatstroke counts are conservative and ecological; a 365-day window gives one hot season, so multi-year variability is absent. Do not use for real risk estimation or policy.

## Example: analogue search (hypothetical day: WBGT 32.5, Tmax 38.1, RH 64%, 3 consecutive heat days)
Fields used: {', '.join(ana['features_used'])}.

**CURRENT THERMAL RISK:** {ana['CURRENT_THERMAL_RISK']}

**HISTORICAL ANALOGUES (top 5):**

{md_table(ana['HISTORICAL_ANALOGUE'], index=False)}

**EXPECTED HEALTH IMPACT:** {ana['EXPECTED_HEALTH_IMPACT']}

**VULNERABLE POPULATIONS:** {ana['VULNERABLE_POPULATIONS']}

**RECOMMENDED PRECAUTIONS:** {ana['RECOMMENDED_PRECAUTIONS']}

*Decision-support indicator, not an individual medical prediction.*
"""
    (out / "mortality_validation_report.md").write_text(rep, encoding="utf-8")
    print("beta", beta, "R", R_mean, R_states)
    print(st.round(2).to_string()); print(cat.round(3).to_string()); print(hwp.round(3).to_string()); print(sp.to_string())
    print("MF", mf, hmf, "age", (ageT / ageT.sum()).round(3).to_dict())

if __name__ == "__main__":
    main()
