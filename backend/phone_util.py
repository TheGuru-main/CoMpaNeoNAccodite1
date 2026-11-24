"""Phone normalization."""
import re
from typing import Optional, List

DIAL_CODES = {
    "NG": "234", "GH": "233", "KE": "254", "ZA": "27", "EG": "20",
    "ET": "251", "MA": "212", "CM": "237", "CI": "225", "UG": "256",
    "US": "1", "GB": "44", "IN": "91", "CA": "1", "AU": "61",
    "DE": "49", "FR": "33", "CN": "86", "BR": "55", "AE": "971",
}
COUNTRY_FOR_CODE = {v: k for k, v in DIAL_CODES.items()}

def normalize_phone(phone: Optional[str], default_country: str = "NG") -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return ""
    cc = DIAL_CODES.get(default_country, "234")
    if digits.startswith(cc) and len(digits) >= len(cc) + 7:
        return "+" + digits
    if digits.startswith("0") and len(digits) >= 10:
        return "+" + cc + digits[1:]
    if len(digits) == 10:
        return "+" + cc + digits
    return "+" + digits

def variants(phone: Optional[str]) -> List[str]:
    if not phone:
        return []
    canonical = normalize_phone(phone)
    if not canonical:
        return []
    raw = re.sub(r"\D", "", str(phone))
    out = [canonical, raw, "+" + raw]
    if canonical.startswith("+234"):
        local = canonical[4:]
        out += ["0" + local, local, "234" + local]
    seen, result = set(), []
    for v in out:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result

def looks_like_phone(s: str) -> bool:
    digits = re.sub(r"\D", "", s or "")
    return 7 <= len(digits) <= 15

# --- P0 country_to_iso (append) ---
COUNTRY_NAME_TO_ISO = {
    "nigeria": "NG", "ghana": "GH", "kenya": "KE", "south africa": "ZA",
    "egypt": "EG", "ethiopia": "ET", "morocco": "MA", "cameroon": "CM",
    "ivory coast": "CI", "cote d'ivoire": "CI", "uganda": "UG",
    "united states": "US", "usa": "US", "united kingdom": "GB", "uk": "GB",
    "india": "IN", "canada": "CA", "australia": "AU", "germany": "DE",
    "france": "FR", "china": "CN", "brazil": "BR", "united arab emirates": "AE",
    "uae": "AE",
}

def country_to_iso(name_or_iso: str | None) -> str:
    """Map registration country name or ISO to 2-letter. Default NG only when missing."""
    if not name_or_iso:
        return "NG"
    s = str(name_or_iso).strip()
    if len(s) == 2 and s.isalpha():
        return s.upper()
    return COUNTRY_NAME_TO_ISO.get(s.lower(), "NG")
