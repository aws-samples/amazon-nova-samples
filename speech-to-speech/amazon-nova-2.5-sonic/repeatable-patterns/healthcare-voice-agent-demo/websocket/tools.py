"""Demo tools for the Nova 2.5 Sonic voice agent demo.

Flow: lab_test flags an elevated result -> the agent offers a specialist
follow-up -> check_specialist_availability returns real upcoming Fridays
(computed in Python from the actual current date, never left to the model
to compute) -> book_appointment confirms using the tool's own returned
values, never an invented date/time/confirmation code.

All data is fictional demo data, not any real customer's.
"""

import logging
import uuid
from datetime import datetime, timedelta

from strands import tool

logger = logging.getLogger(__name__)

PATIENT_FIRST_NAME = "Jamie"
PATIENT_LAST_NAME = "Rivera"
PATIENT_PHONE = "+15555550123"
PATIENT_PREFERRED_DAY = "Friday"
PATIENT_MEDICATION = "Metformin 500mg"

SPECIALIST_NAME = "Dr. Patel, Endocrinology"
SLOT_TIMES = ["10:00 AM", "2:00 PM", "11:30 AM"]
PHARMACY_NAME = "Nova Care Pharmacy"
INSURANCE_PLAN_NAME = "Nova Health Plan PPO"


@tool(
    name="lab_test",
    description="User needs to access any lab test results. All parameters are required.",
    inputSchema={
        "json": {
            "type": "object",
            "properties": {
                "first_name": {"description": "Patient's first name", "examples": [], "type": "string"},
                "last_name": {"description": "Patient's last name", "examples": [], "type": "string"},
                "mobile_phone": {
                    "description": "A valid phone number with country code. Patient's mobile phone.",
                    "examples": [],
                    "pattern": r"\+?\d{0,3}\s?\(?\d{1,4}\)?[-\s]?\d{1,4}[-\s]?\d{1,4}[-\s]?\d{1,4}",
                    "type": "string",
                },
            },
            "required": ["mobile_phone", "last_name", "first_name"],
        }
    },
)
def lab_test(first_name: str, last_name: str, mobile_phone: str) -> dict:
    logger.info(f"DEMO LAB_TEST: first_name={first_name!r} last_name={last_name!r} mobile_phone={mobile_phone!r}")
    # Elevated on purpose, to drive the specialist-follow-up branch of the demo.
    return {"hba1c": 8.2, "haemoglobin": 14, "hba1c_status": "elevated", "hba1c_normal_range": "below 5.7"}


@tool(
    name="check_specialist_availability",
    description="Look up the next available specialist appointment slots. No parameters needed.",
    inputSchema={"json": {"type": "object", "properties": {}, "required": []}},
)
def check_specialist_availability() -> dict:
    """Computed in Python from the real current date -- the model never
    has to resolve "next Friday" itself, it only reads this back."""
    today = datetime.now()
    days_until_friday = (4 - today.weekday()) % 7  # Monday=0 ... Friday=4
    days_until_friday = days_until_friday or 7  # if today IS Friday, offer next week's first
    first_friday = today + timedelta(days=days_until_friday)

    slots = []
    for i in range(3):
        slot_date = first_friday + timedelta(weeks=i)
        slots.append({
            "date": slot_date.strftime("%A, %B %-d"),
            "time": SLOT_TIMES[i % len(SLOT_TIMES)],
            "specialist": SPECIALIST_NAME,
        })

    logger.info(f"DEMO CHECK_SPECIALIST_AVAILABILITY: returning {slots}")
    return {"slots": slots}


@tool(
    name="book_appointment",
    description="Book a specialist appointment at a specific date and time returned by check_specialist_availability. All parameters are required.",
    inputSchema={
        "json": {
            "type": "object",
            "properties": {
                "date": {"description": "The exact date string from check_specialist_availability's slots.", "type": "string"},
                "time": {"description": "The exact time string from check_specialist_availability's slots.", "type": "string"},
            },
            "required": ["date", "time"],
        }
    },
)
def book_appointment(date: str, time: str) -> dict:
    confirmation_code = "SC-" + uuid.uuid4().hex[:6].upper()
    logger.info(f"DEMO BOOK_APPOINTMENT: date={date!r} time={time!r} confirmation_code={confirmation_code}")
    return {
        "status": "booked",
        "date": date,
        "time": time,
        "specialist": SPECIALIST_NAME,
        "confirmation_code": confirmation_code,
    }


@tool(
    name="request_prescription_refill",
    description="Request a refill of a medication the caller currently takes. All parameters are required.",
    inputSchema={
        "json": {
            "type": "object",
            "properties": {
                "first_name": {"description": "Patient's first name", "examples": [], "type": "string"},
                "last_name": {"description": "Patient's last name", "examples": [], "type": "string"},
                "mobile_phone": {
                    "description": "A valid phone number with country code. Patient's mobile phone.",
                    "examples": [],
                    "pattern": r"\+?\d{0,3}\s?\(?\d{1,4}\)?[-\s]?\d{1,4}[-\s]?\d{1,4}[-\s]?\d{1,4}",
                    "type": "string",
                },
                "medication_name": {"description": "The medication the caller wants refilled, as they said it.", "examples": ["metformin"], "type": "string"},
            },
            "required": ["mobile_phone", "last_name", "first_name", "medication_name"],
        }
    },
)
def request_prescription_refill(first_name: str, last_name: str, mobile_phone: str, medication_name: str) -> dict:
    logger.info(
        f"DEMO REQUEST_PRESCRIPTION_REFILL: first_name={first_name!r} last_name={last_name!r} "
        f"mobile_phone={mobile_phone!r} medication_name={medication_name!r}"
    )
    on_file = medication_name.strip().lower() in PATIENT_MEDICATION.lower()
    if not on_file:
        return {"status": "not_on_file", "medication_requested": medication_name}

    ready_date = (datetime.now() + timedelta(days=1)).strftime("%A, %B %-d")
    return {
        "status": "refill_sent",
        "medication": PATIENT_MEDICATION,
        "pharmacy": PHARMACY_NAME,
        "ready_date": ready_date,
        "ready_time_of_day": "after 2:00 PM",
    }


@tool(
    name="check_insurance_coverage",
    description="Check whether the caller's insurance covers an upcoming specialist appointment. No parameters needed.",
    inputSchema={"json": {"type": "object", "properties": {}, "required": []}},
)
def check_insurance_coverage() -> dict:
    logger.info("DEMO CHECK_INSURANCE_COVERAGE: checking coverage for known caller")
    return {
        "specialist": SPECIALIST_NAME,
        "covered": True,
        "copay": "$25",
        "insurance_plan": INSURANCE_PLAN_NAME,
    }
