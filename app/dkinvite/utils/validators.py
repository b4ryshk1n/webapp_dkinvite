import re

NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё\s\-'.]+$")
SEAT_RE = re.compile(r"^[A-Za-zА-Яа-яЁё0-9\s\-_/№.,()]+$")

def normalize_whitespace(value: str) -> str:
    return " ".join((value or "").strip().split())

def _capitalize_token(token: str) -> str:
    parts = token.split("-")
    parts = [p[:1].upper() + p[1:].lower() if p else p for p in parts]
    return "-".join(parts)

def normalize_person_name(value: str) -> str:
    value = normalize_whitespace(value)

    if not value:
        raise ValueError("ФИО обязательно")
    if len(value) < 3:
        raise ValueError("ФИО слишком короткое")
    if len(value) > 128:
        raise ValueError("ФИО слишком длинное")
    if not NAME_RE.fullmatch(value):
        raise ValueError("ФИО содержит недопустимые символы")

    return " ".join(_capitalize_token(part) for part in value.split())

def normalize_seat(value: str) -> str:
    value = normalize_whitespace(value)

    if not value:
        raise ValueError("Место обязательно")
    if len(value) > 128:
        raise ValueError("Обозначение места слишком длинное")
    if not SEAT_RE.fullmatch(value):
        raise ValueError("Место содержит недопустимые символы")

    low = value.lower().replace(".", "")
    low = re.sub(r"\s+", " ", low).strip()

    patterns = [
        r"^ряд\s*(\d+)\s*место\s*(\d+)$",
        r"^р\s*(\d+)\s*м\s*(\d+)$",
        r"^(\d+)\s*ряд\s*(\d+)\s*место$",
        r"^(\d+)\s*[-/]\s*(\d+)$",
    ]

    for pattern in patterns:
        m = re.fullmatch(pattern, low)
        if m:
            row, seat = m.group(1), m.group(2)
            return f"Ряд {int(row)} Место {int(seat)}"

    return value

def parse_seat_list(value: str) -> list[str]:
    raw_parts = re.split(r"[|\n;]+", value or "")
    cleaned = [part.strip() for part in raw_parts if part.strip()]

    if not cleaned:
        raise ValueError("Укажите хотя бы одно место")

    if len(cleaned) > 100:
        raise ValueError("Слишком много мест за один раз")

    result = []
    seen = set()

    for raw in cleaned:
        seat = normalize_seat(raw)
        key = seat.lower()

        if key in seen:
            raise ValueError(f"Дублируется место в форме: {seat}")

        seen.add(key)
        result.append(seat)

    return result
