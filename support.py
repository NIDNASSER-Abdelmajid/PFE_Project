import requests


def rule_list_downloader(lists: dict) -> None:
    for _list, link in lists.items():
        result = requests.get(link["url"])
        open(f"data\\rules_lists\\Lists\\{_list}.txt", "w+", encoding="utf-8").write(result.text)
    return


__all__ = [
    "rule_list_downloader"
]
