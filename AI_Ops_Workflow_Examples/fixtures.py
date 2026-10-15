"""Synthetic fixtures copied from the supplied workbench; no Streamlit imports."""
import random
from datetime import datetime, timedelta, timezone

LOBS = ["Commercial", "Medicare", "Medicaid", "Individual", "Dental",
        "Vision", "Behavioral", "Employer"]
PROGRAMS = [{"program": f"{lob} {flow}", "lob": lob, "id": f"P{i*3+j+1:02}"}
            for i, lob in enumerate(LOBS)
            for j, flow in enumerate(["Enrollment", "Outreach", "Renewals"])]
IMPACTED = ["P01", "P04", "P07", "P10", "P13", "P16"]
BEFORE = '''def build_delivery(payload):
    contact = payload.get("contact", {})
    email = contact.get("email")
    if not email:
        raise ValueError("Missing contact.email")
    return {"recipient": email, "template": payload["template"]}
'''
AFTER = '''def build_delivery(payload):
    contact = payload.get("contact", {})
    email = contact.get("emailAddress")
    if not email:
        raise ValueError("Missing contact.emailAddress")
    return {"recipient": email, "template": payload["template"]}
'''
SAMPLE = {"contact": {"email": "synthetic@example.invalid"}, "template": "enrollment-v1"}
KNOWLEDGE = [
    ("RB-101", "Adobe delivery payload contract", "Adobe adapter v2.4.0 expects contact.email. If upstream producers still send contact.email but an adapter expects contact.emailAddress, recipient mapping fails. Compare code and payload contracts before changing producers. Roll back adapter, validate a canary, then replay only failed message IDs using idempotency keys."),
    ("INC-204", "Past incident: recipient field rename", "A synthetic historical release renamed contact.email to contact.emailAddress. Enrollment communications failed with MISSING_RECIPIENT across multiple programs. Restoring the previous mapping and replaying failed messages resolved the incident. Verify downstream reporting catch-up independently."),
    ("RB-102", "Splunk ingestion lag", "Delayed Splunk indexing can produce stale dashboards. Compare event timestamp with ingestion timestamp. Check indexer health and forwarder queues. Do not roll back an application solely because logs arrive late."),
    ("RB-103", "Adobe rate limiting", "HTTP 429 indicates capacity or throttling. Back off with jitter, inspect tenant quotas, and reduce concurrency. Payload contract errors do not benefit from retry storms."),
    ("RB-104", "Reporting backlog recovery", "After communication recovery, verify reporting checkpoint progress and queue depth. Replay with message-level idempotency and preserve original failure records for audit. Success must be supported by post-recovery evidence."),
    ("RB-105", "Release rollback controls", "Require operator approval, identify previous version, validate a canary payload, stop if failures persist, then replay failed messages. In this demo rollback and replay only update synthetic state; no deployment API is invoked."),
    ("INC-205", "Expired connector certificate", "TLS handshake failures across all requests were caused by an expired integration certificate. Certificate replacement resolved transport errors. No payload mapping defect was present."),
    ("RB-106", "Database connection saturation", "Investigate pool checkout latency, active connections and slow queries. Confirm saturation from metrics before resizing. Database congestion is distinct from recipient validation exceptions."),
]


def now():
    return datetime.now(timezone.utc)


def fixture():
    rng = random.Random(44)
    start = now() - timedelta(minutes=60)
    rows = []
    for minute in range(60):
        for p in PROGRAMS:
            rows.append(dict(run_id="", minute=minute, timestamp=start+timedelta(minutes=minute),
                             program_id=p["id"], program=p["program"], lob=p["lob"],
                             attempted=rng.randint(180, 360), failed=0, backlog=0,
                             latency_ms=rng.randint(65, 145), source="Adobe simulator",
                             deployment="REL-240", error_code="", message="Delivery batch completed"))
    return rows

