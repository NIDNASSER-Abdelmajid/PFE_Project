import json
from checker import ADChecker
from adblockparser import AdblockRule


class AdTester:
    def __init__(self, rules_file="data/rules_lists/parsed_rules/EasyList.json"):
        self.verifier = ADChecker(json_file=rules_file)
        self.adblock_rules = self._load_rules(rules_file)

    @staticmethod
    def _load_rules(rules_file):
        with open(rules_file, "r", encoding="utf-8") as f:
            rules_json = json.load(f)

        rules = []
        for rule in rules_json.get("blocking", []):
            if raw_rule := rule.get("raw"):
                try:
                    rules.append(AdblockRule(raw_rule))
                except Exception as e:
                    print(f"Error parsing rule: {raw_rule}, Error: {e}")
                    continue
        return rules

    def test_url(self, url, asset_type=None):
        options = []
        for _type in asset_type:
            if _type == "type":
                options.append(asset_type[_type])
            else:
                options.append(_type) if asset_type[_type] else None
        my_parser, my_rule_id = (self.verifier.should_block
                                 (url, [option.lower() for option in options] if options else []))
        options = {option.lower(): True for option in options}
        other_parser = any(
            rule.match_url(url, options)
            for rule in self.adblock_rules
            if rule.matching_supported(options)
        )
        return my_parser, other_parser, my_rule_id if my_rule_id else -1