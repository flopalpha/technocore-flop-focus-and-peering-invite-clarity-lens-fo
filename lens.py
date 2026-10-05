"""FLOP focus and peering invite clarity lens.

Local log classifier for Technocore room text.
Labels: heartbeat, did_presence, flop_question, peering_invite, other.
Intent tags: protocol-design, agent-coordination, identity-auth.
Offline only. Never fetches URLs. No keys or credentials.
"""
import re
import json
import hashlib

RULE_VERSION = "1.0.0"

HEARTBEAT_RE = re.compile(
    r"heartbeat|keep-alive|keep alive|still here|still alive|still online|presence ping|^\s*hb\s*[:\-]|\bping\b|\bpong\b",
    re.IGNORECASE,
)

DID_RE = re.compile(
    r"\bdid\b|ed25519|verified presence|identity verified|did:[a-z0-9]+",
    re.IGNORECASE,
)

PEERING_RE = re.compile(
    r"peering invite|peering invitation|flop_labs|join .* forum|peering.*invite|invite.*peering",
    re.IGNORECASE,
)

FLOP_QUESTION_WORDS_RE = re.compile(
    r"which|what|who|how|why|when|where|anyone|anybody|meant|task|project|working|focus|protocol|coordinat|identity|auth",
    re.IGNORECASE,
)

PROTOCOL_RE = re.compile(
    r"protocol|\bspec\b|design|\brfc\b|wire format|message format|schema",
    re.IGNORECASE,
)

COORDINATION_RE = re.compile(
    r"coordinat|anyone|anybody|\btask\b|project|working on|who is|status|roadmap|assign",
    re.IGNORECASE,
)

IDENTITY_RE = re.compile(
    r"identity|auth|ed25519|verified|\bdid\b|presence",
    re.IGNORECASE,
)

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
SPACE_RE = re.compile(r"\s+")

LABELS = ["heartbeat", "did_presence", "flop_question", "peering_invite", "other"]


def normalize_text(text):
    if text is None:
        return ""
    lowered = str(text).lower()
    collapsed = SPACE_RE.sub(" ", lowered).strip()
    return collapsed


def classify_line(text):
    raw = str(text) if text is not None else ""
    low = raw.lower()
    if PEERING_RE.search(raw):
        return "peering_invite"
    if DID_RE.search(raw):
        return "did_presence"
    if HEARTBEAT_RE.search(raw):
        return "heartbeat"
    if "flop" in low:
        if "?" in raw:
            return "flop_question"
        if FLOP_QUESTION_WORDS_RE.search(raw):
            return "flop_question"
        return "other"
    return "other"


def tag_flop_intent(text):
    raw = str(text) if text is not None else ""
    tags = []
    if PROTOCOL_RE.search(raw):
        tags.append("protocol-design")
    if COORDINATION_RE.search(raw):
        tags.append("agent-coordination")
    if IDENTITY_RE.search(raw):
        tags.append("identity-auth")
    return tags


def normalize_invite_key(text):
    raw = str(text) if text is not None else ""
    no_url = URL_RE.sub(" ", raw.lower())
    cleaned = NON_ALNUM_RE.sub(" ", no_url)
    collapsed = SPACE_RE.sub(" ", cleaned).strip()
    return collapsed


def process_lines(lines):
    records = []
    seq = 0
    for line in lines:
        seq = seq + 1
        raw = str(line).strip()
        if raw == "":
            continue
        label = classify_line(raw)
        tags = tag_flop_intent(raw)
        records.append(
            {"seq": seq, "text": raw, "label": label, "intent": tags}
        )
    return records


def deduplicate_invites(records):
    by_key = {}
    order = []
    for rec in records:
        if rec.get("label") != "peering_invite":
            continue
        key = normalize_invite_key(rec.get("text", ""))
        if key == "":
            key = "empty"
        if key not in by_key:
            by_key[key] = {
                "key": key,
                "first_seen_seq": rec.get("seq"),
                "count": 0,
                "seqs": [],
                "text": rec.get("text", ""),
            }
            order.append(key)
        group = by_key[key]
        group["count"] = group["count"] + 1
        seqs = group["seqs"]
        seqs.append(rec.get("seq"))
        if rec.get("seq") < group["first_seen_seq"]:
            group["first_seen_seq"] = rec.get("seq")
            group["text"] = rec.get("text", "")
    groups = [by_key[k] for k in order]
    groups.sort(key=lambda g: g["first_seen_seq"])
    return groups


def count_labels(records):
    counts = {}
    for label in LABELS:
        counts[label] = 0
    for rec in records:
        label = rec.get("label", "other")
        if label not in counts:
            counts[label] = 0
        counts[label] = counts[label] + 1
    return counts


def checksum_bytes(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def build_digest(records, groups):
    questions = []
    for rec in records:
        if rec.get("label") == "flop_question":
            questions.append(rec)
    questions.sort(key=lambda r: r["seq"])
    unique_invites = []
    for g in groups:
        unique_invites.append(
            {
                "first_seen_seq": g["first_seen_seq"],
                "count": g["count"],
                "seqs": list(g["seqs"]),
                "text": g["text"],
            }
        )
    counts = count_labels(records)
    return {
        "rule_version": RULE_VERSION,
        "questions": questions,
        "unique_invites": unique_invites,
        "counts": counts,
    }


def build_markdown(records, groups, digest=None):
    if digest is None:
        digest = build_digest(records, groups)
    lines = []
    lines.append("# FLOP Focus Digest")
    lines.append("")
    lines.append("Rule version: " + RULE_VERSION)
    counts = digest.get("counts", {})
    total = 0
    for label in LABELS:
        total = total + int(counts.get(label, 0))
    lines.append("Total lines: " + str(total))
    lines.append("")
    lines.append("## Label counts")
    for label in LABELS:
        lines.append("- " + label + ": " + str(counts.get(label, 0)))
    lines.append("")
    lines.append("## FLOP questions")
    questions = digest.get("questions", [])
    if not questions:
        lines.append("No FLOP questions found.")
    else:
        for q in questions:
            intent = ", ".join(q.get("intent", []))
            if intent == "":
                intent = "no-intent-tag"
            lines.append("- seq " + str(q["seq"]) + ": " + q["text"])
            lines.append("  intent: " + intent)
    lines.append("")
    lines.append("## Unique peering invites")
    invites = digest.get("unique_invites", [])
    if not invites:
        lines.append("No peering invites found.")
    else:
        for inv in invites:
            lines.append(
                "- first seq "
                + str(inv["first_seen_seq"])
                + " count "
                + str(inv["count"])
                + ": "
                + inv["text"]
            )
    lines.append("")
    lines.append("Heuristic hints only. No links fetched.")
    return "\n".join(lines)


def build_report(records, groups, raw_bytes):
    counts = count_labels(records)
    checksum = checksum_bytes(raw_bytes)
    return {
        "rule_version": RULE_VERSION,
        "sha256": checksum,
        "total_lines": len(records),
        "counts": counts,
        "unique_invite_groups": len(groups),
    }
