"""Public synthetic fixtures assembled at runtime; no live credentials."""


def samples() -> dict[str, str]:
    return {
        "aws-access-key": "AKIA" + "7ZQ2" * 4,
        "github-token": "ghp_" + "aB7z" * 9,
        "slack-token": "xoxb-" + "123456-" + "AbCdEf123456",
        "google-api-key": "AIza" + "bC7" * 11 + "qZ",
        "stripe-live-key": "sk_" + "live_" + "aB7z" * 8,
        "jwt": "eyJ" + "hYmNkZWY" + "." + "aBcDeF12" + "." + "ZyXwVu98",
        "private-key": "-----BEGIN " + "PRIVATE KEY-----",
        "credential-assignment": "mangoCedar7riverStone",
        "basic-auth-url": "reader:" + "synthetic-pass-42",
        "high-entropy": "aB3dE6gH9jK2mN5pQ8sT1vW4yZ7cF0rL",  # secretscan:ignore
    }


def lines() -> dict[str, str]:
    values = samples()
    values["credential-assignment"] = (
        'password = "' + values["credential-assignment"] + '"'
    )
    values["basic-auth-url"] = "https://" + values["basic-auth-url"] + "@example.org/"
    return values
