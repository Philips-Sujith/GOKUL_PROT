# Ushna Kaappaan — Localized Heat Stress & Early Warning System
> *“From weather conditions to human heat risk.”*
> **SIH 2026 Problem Statement:** Extreme Heatwave Early Warning and Human Thermal Stress Index

---

## 1. Project Overview & Scientific Motivation
**Ushna Kaappaan** (Tamil: *“Heat Protector”*) is a localized, operational public-health and disaster management platform designed specifically for South India covering **83 districts** across:
- **Tamil Nadu** (38 districts)
- **Kerala** (14 districts)
- **Karnataka** (31 districts)

Traditional weather forecasts report ambient dry-bulb temperature (e.g. *“38°C in Chennai”*), which fails to convey the actual physiological strain experienced by human beings. Human thermoregulation depends simultaneously on **radiation loading (sunlight and ground re-radiation), relative humidity (evaporative sweating capacity), convective air movement (wind speed), and metabolic physical activity**.

Ushna Kaappaan bridges this critical gap by translating live meteorological and downwelling solar radiation streams into the internationally recognized **Universal Thermal Climate Index (UTCI)** and delivering actionable, occupational early-warning advisories and state-level mortality risk context.

---

## 2. System Architecture

```
[ Open-Meteo Weather API ]
        │ (Batch Fetching / Caching)
        ▼
[ WeatherDataProvider Layer ]
        │ (Air Temp, RH, Wind 10m, Shortwave & Direct Radiation, Pressure)
        ▼
[ Scientific Thermal Stress Layer (ECMWF thermofeel) ]
   ├── Solar Geometry Engine (NOAA / Spencer 1971 Zenith Angle & cossza)
   ├── Mean Radiant Temperature (MRT) (Di Napoli et al. 2020)
   ├── Water Vapour Pressure (Magnus-Tetens)
   └── Universal Thermal Climate Index (UTCI) (Brode et al. 2012)
        │
        ├──► [ Authoritative UTCI Category Classification ]
        │          │
        │          ├──► [ Population & Occupation Profile Layer (9 Profiles) ]
        │          │          └── Tailored Precautions, Hydration & Symptoms Watch
        │          │
        │          └──► [ Operational Alert Engine ]
        │                     ├── Deduplication & Cooldown Cache (4 Hours)
        │                     ├── Role Channel Routing (Municipality, Health, Unions, Public)
        │                     └──► [ Telegram Notification Service ] (Real Bot / Mock Transport)
        │
        └──► [ State-Level Mortality Model (ML Inference Engine) ]
                   ├── Preprocessed 39 Non-Leaking Predictors
                   ├── Trained Pipeline Artifact (Ridge Regression)
                   └── Continuous Mortality Estimate (per 100,000) & Risk Context (State-Level Only)
```

---

## 3. Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Leaflet GIS, Recharts, Lucide Icons |
| **Backend** | Python 3.14 / FastAPI, Uvicorn, SQLAlchemy ORM, Pydantic |
| **Scientific Computing** | ECMWF `thermofeel` (v2.3.0), NumPy, SciPy |
| **Machine Learning** | `scikit-learn` (v1.9.1), `joblib`, `pandas` |
| **GIS & Mapping** | Leaflet.js, Static South India 83-District GeoJSON, CartoDB Positron Light Basemap |
| **Database** | SQLite (Default embedded) / MySQL 8.0 support via SQLAlchemy |
| **Alerting** | Telegram Bot API / Automated Mock Delivery Transport |

---

## 4. Scientific Methodology

### A. Solar Geometry
To accurately compute solar irradiance angles for every district:
- Fractional Year: $\gamma = \frac{2\pi}{365}(N - 1 + \frac{\text{hour} - 12}{24})$
- Solar Declination ($\delta$) and Equation of Time ($EqT$) calculated via Spencer (1971).
- Cosine of Solar Zenith Angle ($\cos\theta_z$) clamped to $[0.0, 1.0]$.

### B. Mean Radiant Temperature (MRT)
MRT represents the uniform temperature of an imaginary enclosure in which radiant heat transfer from the human body equals the actual non-uniform radiant transfer. Implemented via **ECMWF thermofeel** (`thermofeel.calculate_mean_radiant_temperature`) following **Di Napoli et al. (2020)**:
- $ssrd$: Surface solar radiation downwards ($W/m^2$)
- $ssr$: Surface net solar radiation ($W/m^2$) with terrestrial albedo $\alpha = 0.20$
- $dsrp$: Direct solar radiation perpendicular to beam $= \frac{fdir}{\cos\theta_z}$
- $strd$: Atmospheric downwelling thermal radiation (Stefan-Boltzmann with Idso-Jackson emissivity)
- $strr$: Net surface thermal radiation

### C. Universal Thermal Climate Index (UTCI)
Calculated via **ECMWF thermofeel** (`thermofeel.calculate_utci`) based on the 6th-order polynomial of **Brode et al. (2012)** using $T_{2m}$, $va_{10m}$, $MRT$, and actual water vapour pressure $e_{hPa}$ (Magnus formula).

### D. Authoritative UTCI Thermal Stress Categories
| UTCI Range (°C) | Thermal Stress Category | Physiological Risk |
|---|---|---|
| **> +46.0** | **Extreme heat stress** | Critical emergency; extreme heatstroke risk |
| **+38.0 to +46.0** | **Very strong heat stress** | Severe heat exhaustion, cramps, core hyperpyrexia |
| **+32.0 to +38.0** | **Strong heat stress** | Heavy sweating, cardiovascular strain, fatigue |
| **+26.0 to +32.0** | **Moderate heat stress** | Noticeable heat load on exertion |
| **+9.0 to +26.0** | **No thermal stress** | Thermal comfort / optimal neutral zone |
| **0.0 to +9.0** | **Slight cold stress** | Mild cold sensation; light protective wrap |

---

## 5. Population & Occupational Profile Layer
The platform provides **9 customized profiles**:
1. **General Public**
2. **Outdoor Worker** (Delivery, utility technicians, street vendors)
3. **Farmer** (Agricultural cultivators, open-field labour)
4. **Ground/Construction Labourer** (Masonry, asphalt, roofing)
5. **Corporation Worker** (Sanitation, waste collectors, drainage staff)
6. **IT Worker** (Urban AC-to-outdoor commute transition)
7. **School Student** (Classroom ventilation, water bells, sports restrictions)
8. **College Student** (Campus commutes, two-wheeler hydration)
9. **Senior Citizen** (Cardiovascular vulnerability, impaired thirst response)

> **CRITICAL SCIENTIFIC BOUNDARY:**
> Selecting an occupation/profile modifies the **actionable precautions, exposure directives, and symptoms watch**. It **NEVER modifies the underlying meteorological data, Mean Radiant Temperature, or scientific UTCI calculation**.

---

## 6. State-Level Mortality Machine Learning Model

### Model Architecture & Training
- **Target Column:** `heat_related_mortality_rate_per_100000` (Continuous daily rate per 100,000 population)
- **Calibration Reference:** Guin, Bhan & Sethi (2025), *Temperature* 12(2):179-199
- **Predictor Features (39 Total):** Temperature anomalies, humidity burden, WBGT, nighttime heat stress, exposure lags ($t-1, t-2, t-3, t-7$), cumulative 3-day and 7-day heat loads, healthcare access, cooling access, and demographic age buckets.
- **Zero Target Leakage:** Strictly excludes raw death counts, components, expectations, and anomaly targets.
- **Validation Scheme:** Temporal train/test split (75% train, 25% future test split on date).
- **Candidate Models Evaluated:** Ridge Regression, ElasticNet, Random Forest, Gradient Boosting, Extra Trees.
- **Selected Production Model:** **Ridge Regression Pipeline** (`backend/artifacts/mortality_model/mortality_model_pipeline.joblib`).
  - **Temporal Test RMSE:** `0.000431`
  - **Temporal Test MAE:** `0.000262`
  - **Temporal Test $R^2$:** `0.1894`
  - **Pearson Correlation ($r$):** `0.4421`

### Strict Public Health Limitation & State-Only Policy
- **Synthetic Baseline:** The underlying training dataset is synthetic calibration data. Model estimates are prototype research indicators, **NOT official NCRB or IMD mortality statistics**.
- **State-Level Only:** The model operates strictly at state-level aggregation (**Tamil Nadu, Kerala, Karnataka**). Distributing state predictions into district-level mortality figures is scientifically invalid and strictly disallowed.

---

## 7. Operational Alert Engine & Telegram Integration

### Operational Severity vs Scientific UTCI
Operational severities are application-level dispatch levels distinct from scientific UTCI categories:
- **LOW** (UTCI < 32°C) $\rightarrow$ Dashboard monitoring only.
- **MODERATE** (32°C $\le$ UTCI < 38°C) $\rightarrow$ Public Health Advisory.
- **HIGH** (38°C $\le$ UTCI < 42°C) $\rightarrow$ Municipality Authorities + Public Health Centres.
- **SEVERE** (42°C $\le$ UTCI < 46°C) $\rightarrow$ Municipalities + PHCs + Worker Union Leaders.
- **EXTREME** (UTCI $\ge$ 46°C) $\rightarrow$ Municipalities + PHCs + Worker Union Leaders + General Public.

### Telegram Notification Modes
- **Configured Mode:** When `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured in `.env`, messages are dispatched over the official Telegram Bot API.
- **Mock / Test Mode:** When credentials are unconfigured, the system automatically uses the **MOCK/TEST Transport Mode**, recording full payload and delivery logs in the audit database without failing or fabricating deliveries.
- **Cooldown & Deduplication:** 4-hour cooldown prevents spamming identical alerts for unchanged conditions.
- **Manual Escalation:** Admin portal allows immediate custom directive broadcast.

---

## 8. Application Modes

- **LIVE MODE:** Batches live weather observations from Open-Meteo REST API across all 83 district coordinates, computes real-time MRT and UTCI via thermofeel, evaluates alerts, and logs audit traces.
- **DEMO MODE:** Provides 5 controlled physical scenarios:
  1. `NORMAL` (Baseline comfortable day)
  2. `MODERATE_HEAT` (Warm afternoon)
  3. `HIGH_HEAT_STRESS` (Elevated pre-heatwave)
  4. `SEVERE_HEAT_STRESS` (Severe heatwave)
  5. `EXTREME_HEAT_STRESS` (Critical emergency, UTCI > 46°C)
  *All demo scenarios pass through the genuine thermofeel calculation pipeline without hardcoding outcomes.*

---

## 9. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/system/status` | Current system health, active alerts, mode, and timestamps |
| `POST` | `/api/system/mode` | Switch application mode between `LIVE` and `DEMO` |
| `POST` | `/api/system/refresh` | Trigger manual weather ingestion and thermal computation cycle |
| `GET` | `/api/districts` | List all 83 districts with current thermal results and coordinates |
| `GET` | `/api/districts/{id}` | Detailed district view with 24-hour historical trend |
| `GET` | `/api/thermal/latest` | Regional thermal overview, category distributions, and state averages |
| `GET` | `/api/population-profiles`| List all 9 occupational and population profiles |
| `GET` | `/api/health-impact/{districtId}` | Profile-specific health advisory and precautions |
| `GET` | `/api/mortality/overview` | State-level continuous mortality estimates and model metadata |
| `GET` | `/api/alerts` | Active operational alerts and Telegram delivery audit log |
| `POST` | `/api/admin/login` | Administrator authentication |
| `POST` | `/api/admin/escalations/send` | Admin manual escalation broadcast |
| `POST` | `/api/admin/reports/generate` | Official synthesis report generator |

---

## 10. Local Setup & Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Clone and Configure Environment
```bash
cp .env.example .env
```

### 2. Install Python Dependencies & Train ML Model
```bash
pip install -r requirements.txt
python ml_pipeline/train_mortality_model.py
```

### 3. Build Frontend & Run Backend Server
```bash
# Build frontend
cd frontend
npm install
npm run build
cd ..

# Start FastAPI server (serves both API and UI)
python backend/main.py
```
Open **`http://localhost:8000`** in your web browser.

### 4. Running Tests
```bash
python -m pytest -v tests/
```

---

## 11. Project Owners & Credentials Note
To activate real Telegram broadcasts:
1. Create a Telegram Bot via `@BotFather` and obtain your Bot Token.
2. Retrieve your Target Channel/Group Chat ID.
3. Set in `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```
4. Restart the backend server. The system will automatically switch transport mode from `MOCK` to `REAL`.

---

## 12. Scientific & Public Health Disclaimers
1. **Educational & Decision Support:** Ushna Kaappaan is built as a decision support and early-warning prototype for public health authorities and citizens.
2. **General Health Advisory:** Health precautions and symptom checklists provide general heat-health guidance and do not constitute clinical diagnosis or medical prescription.
3. **Synthetic Mortality Data:** The mortality prediction layer is trained on synthetic statistical data (Guin et al. 2025 calibration). Production casualty forecasting requires authorized real-world clinical and epidemiological surveillance registry data.
