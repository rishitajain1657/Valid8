"""Deterministic clinical safety gate for Valid8 pre-triage.

Rules follow ACOG obstetric hemorrhage shock-index practice and NICE-aligned
emergency triage logic for atypical female ischemic presentations and
pulse-temperature dissociation. This module is a non-diagnostic safety
firewall: it never invents a diagnosis from missing data.
"""

from __future__ import annotations

import math
import re
from typing import Any


OBSTETRIC_STATUSES = frozenset(
    {
        "postpartum",
        "post-partum",
        "post partum",
        "postnatal",
        "post-natal",
        "pregnant",
        "pregnancy",
        "gestational",
        "antenatal",
        "prenatal",
        "intrapartum",
        "puerperium",
        "puerperal",
    }
)

HEMORRHAGE_TERMS = (
    "soak",
    "soaking",
    "soaked",
    "pads",
    "pad",
    "bleeding",
    "bleed",
    "blood clots",
    "clots",
    "hemorrhage",
    "haemorrhage",
    "hemorrhag",
    "haemorrhag",
    "flooding",
    "gushing",
    "heavy period",
    "lochia",
    "passing clots",
)

ATYPICAL_ISCHEMIC_TERMS = (
    "jaw",
    "mandible",
    "shoulder",
    "scapular",
    "scapula",
    "between the shoulder",
    "indigestion",
    "acidity",
    "acid reflux",
    "heartburn",
    "epigastric",
    "burning in chest",
    "chest burn",
    "gastric burn",
)

ISCHEMIC_COMPANION_TERMS = (
    "dyspnea",
    "dyspnoea",
    "shortness of breath",
    "short of breath",
    "breathless",
    "breathlessness",
    "can't breathe",
    "cannot breathe",
    "difficulty breathing",
    "air hunger",
    "nausea",
    "nauseous",
    "nauseated",
    "queasy",
    "vomiting",
    "vomit",
    "sweating",
    "diaphoresis",
    "clammy",
)

GASTROINTESTINAL_TERMS = (
    "diarrhea",
    "diarrhoea",
    "loose stool",
    "loose stools",
    "abdominal",
    "abdomen",
    "stomach pain",
    "stomach ache",
    "belly",
    "vomit",
    "vomiting",
    "nausea",
    "constipation",
    "cramp",
    "cramps",
    "enteric",
    "typhoid",
    "gut",
    "gastro",
    "gi upset",
    "stool",
    "bowel",
    "anorexia",
    "loss of appetite",
    "poor appetite",
    "epigastric",
    "right upper quadrant",
    "ruq",
)

DURATION_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(day|days|hour|hours|hr|hrs|week|weeks|minute|minutes|min|mins)",
    re.IGNORECASE,
)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0))
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _as_int(value: Any) -> int | None:
    number = _as_float(value)
    if number is None:
        return None
    return int(round(number))


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _contains_any(haystack: str, terms: tuple[str, ...]) -> bool:
    lowered = haystack.lower()
    return any(term in lowered for term in terms)


def _normalize_status(value: Any) -> str:
    text = _normalize_text(value).lower().replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    aliases = {
        "non pregnant": "non-pregnant",
        "nonpregnant": "non-pregnant",
        "not pregnant": "non-pregnant",
        "none": "non-pregnant",
        "na": "non-pregnant",
        "gestational": "gestational",
        "pregnant": "gestational",
        "pregnancy": "gestational",
        "antenatal": "gestational",
        "prenatal": "gestational",
        "postpartum": "postpartum",
        "post partum": "postpartum",
        "postnatal": "postpartum",
        "post natal": "postpartum",
        "puerperium": "postpartum",
        "perimenopause": "perimenopause",
        "peri menopause": "perimenopause",
        "perimenopausal": "perimenopause",
        "menopausal": "perimenopause",
        "menopause": "perimenopause",
    }
    return aliases.get(text, text or "unspecified")


def _is_obstetric(status: str) -> bool:
    compact = status.replace("-", " ")
    return compact in OBSTETRIC_STATUSES or any(
        token in compact for token in ("pregnant", "gestational", "postpartum", "postnatal")
    )


def _mean_arterial_pressure(sbp: float | None, dbp: float | None) -> float | None:
    if sbp is None or dbp is None:
        return None
    return round(dbp + (sbp - dbp) / 3.0, 2)


def _pulse_pressure(sbp: float | None, dbp: float | None) -> float | None:
    if sbp is None or dbp is None:
        return None
    return round(sbp - dbp, 2)


def _shock_index(heart_rate: float | None, sbp: float | None) -> float | None:
    if heart_rate is None or sbp is None or sbp <= 0:
        return None
    return round(heart_rate / sbp, 3)


def extract_symptom_duration(symptoms: str, explicit: Any = None) -> str:
    provided = _normalize_text(explicit)
    if provided:
        return provided
    match = DURATION_PATTERN.search(symptoms)
    if not match:
        return "duration not stated"
    quantity = match.group(1)
    unit = match.group(2).lower()
    unit_map = {
        "day": "day",
        "days": "days",
        "hour": "hour",
        "hours": "hours",
        "hr": "hour",
        "hrs": "hours",
        "week": "week",
        "weeks": "weeks",
        "minute": "minute",
        "minutes": "minutes",
        "min": "minute",
        "mins": "minutes",
    }
    canonical = unit_map.get(unit, unit)
    if quantity == "1" and canonical.endswith("s"):
        canonical = canonical[:-1]
    if quantity != "1" and not canonical.endswith("s"):
        canonical = canonical + "s"
    return f"{quantity} {canonical}"


def evaluate_patient_triage(data: dict) -> dict:
    """Apply ordered ACOG/NICE safety gates to a patient intake dictionary.

    Evaluation order is obstetric occult shock, atypical female ischemic
    pattern (MINOCA-risk), enteric pyrexia with Faget's sign, then standard
    triage. First matching gate wins.
    """
    if not isinstance(data, dict):
        raise TypeError("patient data must be a dictionary")

    symptoms = _normalize_text(
        data.get("symptoms")
        or data.get("chief_complaint")
        or data.get("complaint")
        or data.get("subjective")
        or ""
    )
    heart_rate = _as_float(data.get("heart_rate", data.get("hr")))
    sbp = _as_float(data.get("sbp", data.get("systolic")))
    dbp = _as_float(data.get("dbp", data.get("diastolic")))
    temperature = _as_float(
        data.get("temperature", data.get("temp", data.get("oral_temp")))
    )
    age = _as_int(data.get("age"))
    reproductive_status = _normalize_status(
        data.get("reproductive_status", data.get("status", data.get("repro_status")))
    )
    duration = extract_symptom_duration(symptoms, data.get("symptom_duration"))

    shock_index = _shock_index(heart_rate, sbp)
    mean_arterial_pressure = _mean_arterial_pressure(sbp, dbp)
    pulse_pressure = _pulse_pressure(sbp, dbp)

    hemorrhage_language = _contains_any(symptoms, HEMORRHAGE_TERMS)
    obstetric = _is_obstetric(reproductive_status)
    elevated_shock_index = shock_index is not None and shock_index >= 0.9

    if obstetric and (elevated_shock_index or hemorrhage_language):
        result = {
            "urgency_tier": "P1 - Critical",
            "alert_title": "CRITICAL: Elevated Obstetric Shock Index & Occult PPH Risk",
            "alert_detail": (
                "Shock Index >= 0.9. Compensatory vasoconstriction masks falling "
                "blood pressure until circulatory collapse. Immediate bedside "
                "ultrasound to rule out retained products of conception (RPOC) required."
            ),
            "shock_index": shock_index,
            "category": "OBSTETRIC_SHOCK",
        }
    elif _contains_any(symptoms, ATYPICAL_ISCHEMIC_TERMS) and (
        _contains_any(symptoms, ISCHEMIC_COMPANION_TERMS)
        or (heart_rate is not None and heart_rate > 95)
    ):
        result = {
            "urgency_tier": "P1 - Emergent",
            "alert_title": "ISCHEMIC ALERT: Atypical Female Acute Coronary Pattern",
            "alert_detail": (
                "Non-crushing jaw/scapular discomfort with dyspnea. 50% of female "
                "infarctions are misdiagnosed as acid reflux. Immediate 12-lead ECG "
                "and serial hs-cTnI assays recommended."
            ),
            "shock_index": shock_index,
            "category": "CARDIAC_MINOCA",
        }
    elif (
        temperature is not None
        and temperature >= 102.5
        and heart_rate is not None
        and heart_rate < 90
        and _contains_any(symptoms, GASTROINTESTINAL_TERMS)
    ):
        result = {
            "urgency_tier": "P2 - Priority",
            "alert_title": "ACUTE INFECTION: Relative Bradycardia (Faget's Sign)",
            "alert_detail": (
                "Heart rate dissociated from high pyrexia. Suggests enteric bacterial "
                "invasion; complete Blood Culture & Widal panel before empirical antibiotics."
            ),
            "shock_index": shock_index,
            "category": "ENTERIC_FEVER",
        }
    else:
        result = {
            "urgency_tier": "P3 - Standard",
            "alert_title": "STANDARD TRIAGE: No Immediate Red-Flag Safety Gate Triggered",
            "alert_detail": (
                "Current free-text symptoms and home vitals do not meet ACOG occult "
                "postpartum hemorrhage, atypical female ischemic, or Faget-sign enteric "
                "thresholds. Continue structured nursing assessment and escalate if "
                "vitals or language change."
            ),
            "shock_index": shock_index,
            "category": "STANDARD_TRIAGE",
        }

    result.update(
        {
            "mean_arterial_pressure": mean_arterial_pressure,
            "pulse_pressure": pulse_pressure,
            "heart_rate": heart_rate,
            "sbp": sbp,
            "dbp": dbp,
            "temperature": temperature,
            "age": age,
            "reproductive_status": reproductive_status,
            "symptom_duration": duration,
            "symptoms": symptoms,
        }
    )
    return result
