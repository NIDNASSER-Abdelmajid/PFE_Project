import json
import requests


def rule_list_downloader(lists: dict) -> None:
    for _list, link in lists.items():
        result = requests.get(link["url"])
        open(f"data\\rules_lists\\Lists\\{_list}.txt", "w+", encoding="utf-8").write(result.text)
    return

def load_from_json(self, filename: str) -> None:
    """Load rules from JSON file"""
    with open(filename, 'r') as f:
        self.rules = json.load(f)

__all__ = [
    "rule_list_downloader",
    "load_from_json",
]
