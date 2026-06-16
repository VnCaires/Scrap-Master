from __future__ import annotations


def mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def mask_name(first_name: str, last_name: str) -> str:
    first = f"{first_name[:1]}." if first_name else ""
    last = f"{last_name[:1]}." if last_name else ""
    return " ".join(part for part in [first, last] if part) or "***"
