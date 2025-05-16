from typing import Any
import json


def is_valid_json(string: str) -> bool:
    try:
        json.loads(string)  # Пробуем распарсить строку как JSON
        return True
    except json.JSONDecodeError:
        return False


def parse_grpc_detail(detail: dict[str, Any]) -> dict[str, Any]:
    parsed_detail = {}

    for k, v in detail.items():
        if isinstance(v, str) and is_valid_json(v):
            try:
                parsed_detail[k] = json.loads(v)
            except json.JSONDecodeError:
                parsed_detail[k] = v
        else:
            parsed_detail[k] = v

    return parsed_detail
