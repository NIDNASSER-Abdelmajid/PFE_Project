import re
import json
from functools import lru_cache
from rules_parser import ELParser

class Checker:
    def __init__(self, parser=None, json_file=None):
        self.parser = parser if parser else ELParser()
        if json_file:
            self.parser.load_from_json(json_file)

        self._prepare_matchers()
        self._eh_cache = {}

    def _prepare_matchers(self):
        """Pre-compile all regex patterns and organize rules"""
        self._compiled_rules = {
            'blocking': [],
            'exceptions': [],
            'element_hiding': []
        }

        for category in self._compiled_rules:
            for rule in self.parser.rules[category]:
                compiled = re.compile(rule['pattern']) if rule.get('pattern') else None
                self._compiled_rules[category].append((compiled, rule))

    def should_block(self, url, options=None):
        """Optimized single URL check"""
        options = options or {}
        domain = options.get('domain') if isinstance(options, dict) else None

        for compiled, rule in self._compiled_rules['exceptions']:
            if self._check_domains_fast(domain, rule):
                if compiled and compiled.search(url):
                    return False, None

        for compiled, rule in self._compiled_rules['blocking']:
            if self._check_domains_fast(domain, rule):
                if compiled and compiled.search(url):
                    return True, rule['id']

        return False, None

    def get_element_hiding_selectors(self, domain=None):
        """Get element hiding selectors for a domain"""
        selectors = []

        for rule in self.parser.rules['element_hiding']:
            if self._check_domain_restrictions(domain, rule):
                selectors.append(rule['raw'].split('##')[1])

        return selectors

    def _matches_any(self, url, rules, options):
        """Check if URL matches any of the given rules"""
        for rule in rules:
            if self._matches_rule(url, rule, options):
                print(f"Matched rule: {rule['raw']}")
                return True, rule['id']
        return False, None

    def _matches_rule(self, url, rule, options):
        domain = None
        if isinstance(options, list):
            option_list = options
        elif isinstance(options, dict):
            domain = options.get("domain")
            option_list = [opt for opt in options if opt != "domain"]
        else:
            option_list = []

        if rule['options']:
            # print(rule['options'])
            # if not any(opt in option_list and val is True for opt, val in rule['options'].items()):
            #     return False
            if any(opt in option_list and val is False for opt, val in rule['options'].items()):
                return False
        # print(option_list)
        if not self._check_domain_restrictions(domain, rule):
            return False

        if 'compiled_re' in rule:
            # print(rule['compiled_re'])
            if bool(re.compile(rule['pattern']).search(url)):
                return True
        return False

    def _check_domain_restrictions(self, domain, rule):
        """Check if domain matches rule's restrictions"""
        include_domains = rule['domains']['include']
        exclude_domains = rule['domains']['exclude']

        if not include_domains and not exclude_domains:
            return True

        domain_variants = self._get_domain_variants(domain)

        for variant in domain_variants:
            if variant in exclude_domains:
                return False

        if include_domains:
            for variant in domain_variants:
                if variant in include_domains:
                    return True
            return False

        return True

    @lru_cache(maxsize=1024)
    def _get_domain_variants(self, domain):
        """Cached domain variants generation"""
        if not domain:
            return tuple()
        parts = domain.split('.')
        return tuple('.'.join(parts[i:]) for i in range(len(parts)))

    def _check_domains_fast(self, domain, rule):
        """Optimized domain checking"""
        variants = self._get_domain_variants(domain)
        include, exclude = rule['domains']['include'], rule['domains']['exclude']

        if exclude and any(v in exclude for v in variants):
            return False
        if include and not any(v in include for v in variants):
            return False
        return True
