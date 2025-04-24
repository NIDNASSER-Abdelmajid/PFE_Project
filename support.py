import json


def json_loader(_json_file) -> dict:
    with open(_json_file, "r") as f:
        data = json.load(f)
    return data


__all__ = [
    "json_loader"
]