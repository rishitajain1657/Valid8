"""Standardized hospital SBAR synthesis for Valid8 physician hand-off."""

from __future__ import annotations

from typing import Any

from core.rules import extract_symptom_duration


def _fmt(value: Any, digits: int = 1, suffix: str = "") -> str:
    if value is None or value == "":
        return "not recorded"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and digits == 0:
            return f"{int(round(value))}{suffix}"
        if isinstance(value, float):
            rendered = f"{value:.{digits}f}".rstrip("0").rstrip(".")
            return f"{rendered}{suffix}"
        return f"{value}{suffix}"
    return str(value)


def _status_phrase(status: str) -> str:
    mapping = {
        "non-pregnant": "non-pregnant",
        "gestational": "gestational (pregnant)",
        "postpartum": "postpartum",
        "perimenopause": "perimenopausal",
        "unspecified": "reproductive status unspecified",
    }
    return mapping.get(status, status or "reproductive status unspecified")


def _situation(patient_data: dict, triage_result: dict) -> str:
    age = triage_result.get("age", patient_data.get("age"))
    status = triage_result.get(
        "reproductive_status", patient_data.get("reproductive_status", "unspecified")
    )
    symptoms = (
        triage_result.get("symptoms")
        or patient_data.get("symptoms")
        or patient_data.get("chief_complaint")
        or ""
    ).strip()
    duration = triage_result.get("symptom_duration") or extract_symptom_duration(
        symptoms, patient_data.get("symptom_duration")
    )
    complaint = symptoms if symptoms else "no free-text complaint provided"
    age_clause = f"{age}-year-old" if age not in (None, "") else "adult"
    return (
        f"Female {age_clause} patient in the {_status_phrase(str(status))} phase "
        f"presents after {duration} of symptoms. Verbatim subjective complaint: "
        f"\"{complaint}\"."
    )


def _background(triage_result: dict) -> str:
    hr = triage_result.get("heart_rate")
    sbp = triage_result.get("sbp")
    dbp = triage_result.get("dbp")
    temperature = triage_result.get("temperature")
    shock_index = triage_result.get("shock_index")
    mean_ap = triage_result.get("mean_arterial_pressure")
    pulse_pressure = triage_result.get("pulse_pressure")
    bp_text = (
        f"{_fmt(sbp, 0)}/{_fmt(dbp, 0)} mmHg"
        if sbp is not None and dbp is not None
        else "BP not recorded"
    )
    return (
        f"Home vitals at intake — Heart rate {_fmt(hr, 0, ' bpm')}; "
        f"blood pressure {bp_text}; mean arterial pressure "
        f"{_fmt(mean_ap, 1, ' mmHg')} (MAP = DBP + (SBP − DBP) / 3); "
        f"pulse pressure {_fmt(pulse_pressure, 1, ' mmHg')}; oral temperature "
        f"{_fmt(temperature, 1, ' °F')}; Shock Index {_fmt(shock_index, 3)} "
        f"(SI = HR / SBP)."
    )


def _assessment(triage_result: dict) -> str:
    category = triage_result.get("category", "STANDARD_TRIAGE")
    title = triage_result.get("alert_title", "")
    detail = triage_result.get("alert_detail", "")
    shock_index = triage_result.get("shock_index")
    si_clause = (
        f" Calculated Shock Index is {_fmt(shock_index, 3)}."
        if shock_index is not None
        else " Shock Index could not be computed because systolic pressure is missing or zero."
    )

    if category == "OBSTETRIC_SHOCK":
        return (
            f"{title}. Obstetric physiology permits compensatory vasoconstriction that "
            f"preserves a near-normal cuff pressure while circulating volume falls; "
            f"ACOG hemorrhage guidance therefore treats Shock Index ≥ 0.9 and soaking/"
            f"pad/bleeding language as occult postpartum hemorrhage until proven otherwise. "
            f"{detail}{si_clause}"
        )
    if category == "CARDIAC_MINOCA":
        return (
            f"{title}. Female acute coronary syndromes frequently present without crushing "
            f"retrosternal pain. Jaw, scapular, shoulder, or indigestion-type discomfort "
            f"paired with dyspnea, nausea, or sinus tachycardia is treated as an ischemic "
            f"until 12-lead ECG and serial high-sensitivity troponin exclude MINOCA/"
            f"Type 1 infarction. {detail}{si_clause}"
        )
    if category == "ENTERIC_FEVER":
        return (
            f"{title}. Pulse-temperature dissociation (Faget's sign) with gastrointestinal "
            f"complaints is inconsistent with simple viral pyrexia and raises concern for "
            f"invasive enteric infection. Empiric antibiotics before culture acquisition "
            f"will confound isolation. {detail}{si_clause}"
        )
    return (
        f"{title}. No obstetric shock, atypical ischemic, or relative-bradycardia "
        f"infectious gate is currently satisfied. {detail}{si_clause}"
    )


def _recommendation(triage_result: dict) -> str:
    category = triage_result.get("category", "STANDARD_TRIAGE")
    if category == "OBSTETRIC_SHOCK":
        return (
            "Activate obstetric emergency pathway now. STAT bedside pelvic ultrasound to "
            "exclude retained products of conception (RPOC) and intrauterine clot; two "
            "large-bore intravenous cannulae; type and cross-match 4 units; quantitative "
            "blood loss, hemoglobin/hematocrit, fibrinogen, and lactate; uterotonic "
            "readiness and senior obstetric review within minutes. Do not delay imaging "
            "because cuff blood pressure appears preserved."
        )
    if category == "CARDIAC_MINOCA":
        return (
            "Immediate 12-lead ECG with posterior (V7–V9) and right-sided (V4R) leads; "
            "serial high-sensitivity cardiac troponin I at 0 and 1–3 hours; continuous "
            "telemetry; aspirin unless contraindicated; avoid attributing symptoms to "
            "acid reflux until ischemia is excluded. If ECG or hs-cTnI is abnormal, "
            "activate the cardiac catheterization pathway and obtain urgent cardiology "
            "review."
        )
    if category == "ENTERIC_FEVER":
        return (
            "Obtain paired blood cultures and a Widal/enteric panel before the first "
            "dose of antibiotics; complete blood count with differential, CRP, liver "
            "enzymes, and malaria smear if endemic exposure is possible; isolate stool "
            "if diarrhea is present; fluid resuscitation as indicated; infectious "
            "disease review for directed therapy once isolates return. Do not start "
            "empirical broad-spectrum antibiotics until cultures are drawn unless the "
            "patient becomes septic."
        )
    return (
        "Complete a full nursing observation set, repeat vitals in 15–30 minutes, and "
        "re-run this safety gate if language of bleeding, ischemic-equivalent pain, or "
        "high fever appears. Routine laboratory panel as clinically indicated "
        "(CBC, basic metabolic panel). Escalate immediately if Shock Index rises toward "
        "0.9, new dyspnea/jaw-scapular pain develops, or pyrexia with relative "
        "bradycardia emerges."
    )


def generate_sbar_brief(patient_data: dict, triage_result: dict) -> dict:
    """Compose a one-page SBAR physician hand-off from intake plus safety-gate output."""
    if not isinstance(patient_data, dict):
        raise TypeError("patient_data must be a dictionary")
    if not isinstance(triage_result, dict):
        raise TypeError("triage_result must be a dictionary")

    return {
        "situation": _situation(patient_data, triage_result),
        "background": _background(triage_result),
        "assessment": _assessment(triage_result),
        "recommendation": _recommendation(triage_result),
    }
