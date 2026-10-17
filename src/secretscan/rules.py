"""Bounded patterns and deliberately conservative entropy heuristics."""

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass

LEVELS = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    description: str
    pattern: re.Pattern[str]
    group: int = 0


RULES = (
    Rule(
        "aws-access-key",
        "high",
        "AWS access key ID",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    Rule(
        "github-token",
        "high",
        "GitHub classic or fine-grained token",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,255})\b"
        ),
    ),
    Rule(
        "slack-token",
        "high",
        "Slack token",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,180}\b"),
    ),
    Rule(
        "google-api-key",
        "high",
        "Google API key",
        re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"),
    ),
    Rule(
        "stripe-live-key",
        "high",
        "Stripe live secret key",
        re.compile(r"\bsk_live_[A-Za-z0-9]{24,128}\b"),
    ),
    Rule(
        "jwt",
        "medium",
        "JWT-like three-part token",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{5,1021}\.[A-Za-z0-9_-]{8,1024}\.[A-Za-z0-9_-]{8,1024}\b"
        ),
    ),
    Rule(
        "private-key",
        "high",
        "Private key PEM header",
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
        ),
    ),
    Rule(
        "credential-assignment",
        "medium",
        "Credential literal with length/entropy heuristic",
        re.compile(
            r"\b(?:password|secret|token|api_key)\s{0,16}[:=]\s{0,16}[\"']([^\"'\r\n]{1,512})[\"']",
            re.I,
        ),
        1,
    ),
    Rule(
        "basic-auth-url",
        "high",
        "Basic-auth user and password in URL",
        re.compile(r"\bhttps?://([^\s/:@]{1,128}:[^\s/@]{1,256})@", re.I),
        1,
    ),
    Rule(
        "high-entropy",
        "low",
        "High-entropy mixed string",
        re.compile(r"[A-Za-z0-9_+/=-]+"),
    ),
)


def entropy(value: str) -> float:
    """Shannon entropy in bits per character; empty input has zero entropy."""
    size = len(value)
    return -sum((n / size) * math.log2(n / size) for n in Counter(value).values())


def placeholder(value: str) -> bool:
    lower = value.lower()
    return lower in {
        "change" + "me",
        "example",
        "password",
        "secret",
        "token",
    } or lower.startswith(("your_", "example", "${", "<"))


def accepted(rule: Rule, value: str) -> bool:
    if placeholder(value):
        return False
    if rule.id == "credential-assignment":
        return len(value) >= 12 and (entropy(value) >= 3.0 or len(value) >= 24)
    if rule.id == "high-entropy":
        return (
            24 <= len(value) <= 128
            and entropy(value) >= 4.5
            and any(c.islower() for c in value)
            and any(c.isupper() for c in value)
            and any(c.isdigit() for c in value)
        )
    return True


def mask(value: str) -> str:
    return value[:2] + "****" + value[-2:] if len(value) > 4 else "****"


def fingerprint(rule_id: str, path: str, value: str) -> str:
    # NUL delimiters prevent ambiguous concatenation. Full digest in saved data.
    return hashlib.sha256(f"{rule_id}\0{path}\0{value}".encode()).hexdigest()
