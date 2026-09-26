"""
Ushna Kaappaan — Scientific Thermal Stress Service
Implements ECMWF thermofeel for Mean Radiant Temperature (MRT) and Universal Thermal Climate Index (UTCI).
Follows Di Napoli et al. (2020) and Brode et al. (2012).
"""

import math
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
import numpy as np
import thermofeel

from backend.config import settings

# Load authoritative UTCI category thresholds
with open(settings.UTCI_CATEGORIES_FILE, "r") as f:
    UTCI_CATEGORIES = json.load(f)

class ThermalStressService:
    @staticmethod
    def calculate_solar_zenith_angle(lat_deg: float, lon_deg: float, dt_utc: datetime) -> Tuple[float, float]:
        """
        Calculate solar zenith angle and its cosine using standard astronomical formulas (NOAA / Spencer).
        Returns: (cos_zenith_angle, zenith_angle_deg)
        """
        # Day of year
        day_of_year = dt_utc.timetuple().tm_yday
        hour_utc = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        
        # Fractional year in radians
        gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (hour_utc - 12.0) / 24.0)
        
        # Solar declination in radians (Spencer 1971)
        decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
                - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
                - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
        
        # Equation of time in minutes
        eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                           - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
        
        # Solar time in minutes
        time_offset = eqtime + 4.0 * lon_deg
        t_solar = (hour_utc * 60.0 + time_offset) % 1440.0
        
        # Solar hour angle in degrees
        hour_angle_deg = (t_solar / 4.0) - 180.0
        hour_angle_rad = math.radians(hour_angle_deg)
        
        lat_rad = math.radians(lat_deg)
        
        # Cosine of solar zenith angle
        cos_sza = (math.sin(lat_rad) * math.sin(decl) +
                   math.cos(lat_rad) * math.cos(decl) * math.cos(hour_angle_rad))
        
        # Clamp to physical range
        cos_sza = max(0.0, min(1.0, cos_sza))
        sza_deg = math.degrees(math.acos(cos_sza))
        
        return cos_sza, sza_deg

    @staticmethod
    def calculate_vapour_pressure_hpa(temp_c: float, rh_percent: float) -> float:
        """
        Calculates actual water vapour pressure in hPa using the Magnus-Tetens formula.
        """
        # Saturation vapour pressure in hPa
        es = 6.112 * math.exp((17.67 * temp_c) / (temp_c + 243.5))
        ehpa = (max(0.0, min(100.0, rh_percent)) / 100.0) * es
        return float(ehpa)

    @classmethod
    def calculate_mrt(
        cls,
        temp_c: float,
        rh_percent: float,
        shortwave_radiation_wm2: float,
        direct_radiation_wm2: float,
        diffuse_radiation_wm2: float,
        cos_sza: float,
        albedo: float = 0.20
    ) -> float:
        """
        Calculates Mean Radiant Temperature (MRT) in Kelvin using ECMWF thermofeel (Di Napoli et al. 2020).
        """
        temp_k = temp_c + 273.15
        
        # Surface solar radiation downwards [W m-2]
        ssrd = np.array([max(0.0, float(shortwave_radiation_wm2))], dtype=float)
        
        # Surface net solar radiation [W m-2]
        ssr = np.array([float(ssrd[0] * (1.0 - albedo))], dtype=float)
        
        # Total sky direct solar radiation at surface [W m-2]
        fdir = np.array([max(0.0, float(direct_radiation_wm2))], dtype=float)
        
        # Direct solar radiation perpendicular to beam [W m-2]
        cossza_arr = np.array([float(cos_sza)], dtype=float)
        if cossza_arr[0] > 0.05:
            dsrp = np.array([fdir[0] / max(cossza_arr[0], 0.05)], dtype=float)
        else:
            dsrp = fdir
            
        # Thermal downward radiation estimation (Stefan-Boltzmann with atmospheric emissivity)
        sigma = 5.670374e-8
        # Idso-Jackson atmospheric emissivity empirical formula
        vp_hpa = cls.calculate_vapour_pressure_hpa(temp_c, rh_percent)
        emissivity_atm = 1.24 * ((vp_hpa / temp_k) ** (1.0 / 7.0))
        emissivity_atm = min(0.98, max(0.70, emissivity_atm))
        
        strd_val = emissivity_atm * sigma * (temp_k ** 4)
        strd = np.array([float(strd_val)], dtype=float)
        
        # Surface net thermal radiation (typically -50 to -90 W/m2 in tropical daytime)
        strr_val = strd_val - (0.97 * sigma * (temp_k ** 4))
        strr = np.array([float(strr_val)], dtype=float)
        
        # thermofeel calculate_mean_radiant_temperature
        mrt_k_arr = thermofeel.calculate_mean_radiant_temperature(
            ssrd=ssrd,
            ssr=ssr,
            dsrp=dsrp,
            strd=strd,
            fdir=fdir,
            strr=strr,
            cossza=cossza_arr
        )
        
        mrt_k = float(mrt_k_arr[0])
        # Safety physical clamp: MRT typically within -10C to +40C of air temperature
        mrt_k = max(temp_k - 20.0, min(temp_k + 50.0, mrt_k))
        
        return mrt_k

    @classmethod
    def calculate_utci(
        cls,
        temp_c: float,
        rh_percent: float,
        wind_speed_mps: float,
        mrt_k: float
    ) -> float:
        """
        Calculates Universal Thermal Climate Index (UTCI) in Celsius using ECMWF thermofeel (Brode et al. 2012).
        """
        temp_k_arr = np.array([temp_c + 273.15], dtype=float)
        wind_arr = np.array([max(0.5, min(17.0, float(wind_speed_mps)))], dtype=float)
        mrt_k_arr = np.array([float(mrt_k)], dtype=float)
        
        ehpa_val = cls.calculate_vapour_pressure_hpa(temp_c, rh_percent)
        ehpa_arr = np.array([max(0.1, min(50.0, float(ehpa_val)))], dtype=float)
        
        utci_k_arr = thermofeel.calculate_utci(
            t2_k=temp_k_arr,
            va=wind_arr,
            mrt=mrt_k_arr,
            ehPa=ehpa_arr
        )
        
        utci_c = float(utci_k_arr[0] - 273.15)
        return utci_c

    @classmethod
    def classify_utci(cls, utci_c: float) -> Dict[str, Any]:
        """
        Maps a continuous UTCI value in Celsius to the authoritative thermal stress category.
        """
        for cat in UTCI_CATEGORIES:
            if cat["min_utci"] <= utci_c < cat["max_utci"]:
                return cat
                
        # Edge cases
        if utci_c >= 46.0:
            return UTCI_CATEGORIES[0] # Extreme heat stress
        elif utci_c < 0.0:
            return UTCI_CATEGORIES[-1] # Slight cold stress
            
        return UTCI_CATEGORIES[4] # Default No thermal stress

    @classmethod
    def process_district_thermal_stress(
        cls,
        lat: float,
        lon: float,
        dt_utc: datetime,
        temp_c: float,
        rh_percent: float,
        wind_speed_mps: float,
        shortwave_radiation_wm2: float = 0.0,
        direct_radiation_wm2: float = 0.0,
        diffuse_radiation_wm2: float = 0.0
    ) -> Dict[str, Any]:
        """
        Full scientific pipeline: Solar Geometry -> MRT -> UTCI -> Category classification.
        """
        # Validate inputs
        if not (-20.0 <= temp_c <= 60.0 and 0.0 <= rh_percent <= 100.0 and 0.0 <= wind_speed_mps <= 50.0):
            return {
                "mrt_c": temp_c,
                "utci_c": temp_c,
                "category_info": cls.classify_utci(temp_c),
                "data_quality": "INVALID",
                "validation_error": "Input meteorological parameters outside physical bounds"
            }
            
        cos_sza, sza_deg = cls.calculate_solar_zenith_angle(lat, lon, dt_utc)
        
        mrt_k = cls.calculate_mrt(
            temp_c=temp_c,
            rh_percent=rh_percent,
            shortwave_radiation_wm2=shortwave_radiation_wm2,
            direct_radiation_wm2=direct_radiation_wm2,
            diffuse_radiation_wm2=diffuse_radiation_wm2,
            cos_sza=cos_sza
        )
        mrt_c = float(mrt_k - 273.15)
        
        utci_c = cls.calculate_utci(
            temp_c=temp_c,
            rh_percent=rh_percent,
            wind_speed_mps=wind_speed_mps,
            mrt_k=mrt_k
        )
        
        cat_info = cls.classify_utci(utci_c)
        
        return {
            "mrt_c": round(mrt_c, 2),
            "utci_c": round(utci_c, 2),
            "solar_zenith_angle_deg": round(sza_deg, 2),
            "cos_zenith_angle": round(cos_sza, 4),
            "vapour_pressure_hpa": round(cls.calculate_vapour_pressure_hpa(temp_c, rh_percent), 2),
            "category_info": cat_info,
            "data_quality": "VALID"
        }
