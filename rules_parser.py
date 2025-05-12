import itertools
import re
import json


class ELParser:
    id_iter = itertools.count()

    def __init__(self, analysis_type: str = None) -> None:
        self.analysis_type = analysis_type
        self.rules = {
            'blocking': [],
            'exceptions': [],
            'element_hiding': [],
            'element_hiding_exceptions': []
        }
        self.BINARY_OPTIONS = [
            "script", "image", "stylesheet", "object", "xmlhttprequest",
            "object-subrequest", "subdocument", "document", "elemhide",
            "other", "background", "xbl", "ping", "dtd", "media",
            "third-party", "match-case", "collapse", "donottrack", "websocket"
        ]

    def parse_rules(self, rule_texts: list) -> None:
        """Parse multiple adblock rules and categorize them"""
        for rule_text in rule_texts:
            rule = self._parse_single_rule(rule_text.strip())
            if rule:
                self._categorize_rule(rule)

    def _parse_single_rule(self, rule_text: str) -> dict:
        """Parse a single adblock rule"""
        if not rule_text or rule_text.startswith(('!', '[')):
            return {}

        rule = {
            'id': next(self.id_iter),
            'raw': rule_text,
            'is_exception': rule_text.startswith('@@'),
            'is_html_rule': '##' in rule_text or '#@#' in rule_text,
            'options': {},
            'domains': {'include': [], 'exclude': []},
            'type': ''
        }

        if rule['is_exception']:
            rule_text = rule_text[2:]

        if '$' in rule_text:
            options_text = rule_text.split('$')[-1]
            rule_text = rule_text.replace('$' + options_text, '')
            self._parse_options(options_text, rule)

        rule['pattern'] = self._create_regex(rule_text)
        return rule

    def _parse_options(self, options_text, rule) -> None:
        """Parse rule options"""
        options = re.split(r',(?=~?(?:%s))' % ('|'.join(self.BINARY_OPTIONS + ["domain"])), options_text)
        for opt in options:
            if '=' in opt:
                key, value = opt.split('=', 1)
                if key == 'domain':
                    self._parse_domain_restrictions(value, rule)
                else:
                    rule['options'][key] = value
            elif opt.startswith('~'):
                rule['options'][opt[1:]] = False
            else:
                rule['options'][opt] = True

    @staticmethod
    def _parse_domain_restrictions(domains_text, rule) -> None:
        """Parse domain restrictions"""
        domains = domains_text.split('|')
        for domain in domains:
            if domain.startswith('~'):
                rule['domains']['exclude'].append(domain[1:])
            else:
                rule['domains']['include'].append(domain)

    @staticmethod
    def _create_regex(rule_text: str) -> str:
        """Convert adblock rule to regex."""
        if not rule_text:
            return ''

        if rule_text.startswith('/') and rule_text.endswith('/') and len(rule_text) > 1:
            return rule_text[1:-1]

        start_anchor = rule_text.startswith('|')
        end_anchor = rule_text.endswith('|')

        if rule_text.startswith('||'):
            domain = rule_text[2:]
            if '^' in domain:
                domain = domain.split('^')[0]
            domain = re.escape(domain)
            rule = fr"^(?:https?:\/\/)?(?:[^\/?#]+\.)?{domain}"
            if end_anchor:
                rule += r"(?:[\/?#]|$)"
            return rule

        if start_anchor:
            rule_text = rule_text[1:]
        if end_anchor:
            rule_text = rule_text[:-1]

        rule = re.sub(r"([.$+?{}()\[\]\\|])", r"\\\1", rule_text)

        rule = rule.replace("^", r"(?:[^\w\d_\-.%]|$)")
        rule = rule.replace("*", ".*")

        if start_anchor:
            rule = '^' + rule
        if end_anchor:
            rule += '$'

        return rule

    def _categorize_rule(self, rule: dict) -> None:
        """Categorize the rule into appropriate section"""
        if rule['is_html_rule']:
            if rule['is_exception']:
                self.rules['element_hiding_exceptions'].append(rule)
            else:
                self.rules['element_hiding'].append(rule)
        else:
            if rule['is_exception']:
                self.rules['exceptions'].append(rule)
            else:
                self.rules['blocking'].append(rule)

    def save_to_json(self, filename: str) -> None:
        """Save parsed rules to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.rules, f, indent=2)

    def load_from_json(self, filename: str) -> None:
        """Load rules from JSON file"""
        with open(filename, 'r') as f:
            self.rules = json.load(f)
