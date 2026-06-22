import json
import re
from typing import Any


def strip_thought_tags(text: str) -> str:
    cleaned = text.strip()
    if "<thought>" in cleaned and "</thought>" in cleaned:
        cleaned = re.sub(r"<thought>.*?</thought>", "", cleaned, flags=re.DOTALL).strip()
    elif "</thought>" in cleaned:
        cleaned = cleaned.split("</thought>")[-1].strip()
    return cleaned


def parse_json_robustly(text: str) -> dict[str, Any]:
    cleaned = strip_thought_tags(text)

    def _unwrap(value: Any) -> dict[str, Any]:
        if isinstance(value, list) and value:
            value = value[0]
        return value if isinstance(value, dict) else {}

    try:
        return _unwrap(json.loads(cleaned))
    except Exception:
        pass

    if "```" in cleaned:
        for part in cleaned.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") and part.endswith("}"):
                try:
                    return _unwrap(json.loads(part))
                except Exception:
                    continue

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return _unwrap(json.loads(cleaned[start:end + 1]))
        except Exception:
            pass

    return {}
