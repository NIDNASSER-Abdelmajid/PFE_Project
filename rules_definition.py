import re
import json
from settings import *
import requests


class EasyListFilters:
    def __init__(self):
        self.filters = {
            'blocking': [],
            'allow': [],
            'element_hiding': [],
            'element_hiding_exception': [],
            'url_pattern': [],
            'other': []
        }
        self.EASYLIST = requests.get(EASYLIST_URL).text

    def parse(self) -> None:
        """Parse the filter rules and categorize them."""
        for rule in self.EASYLIST.splitlines():
            rule = rule.strip()
            self.process_rule_to_json(rule)


    def categorize(self, rule: str) -> str:
        """Categorize a filter rule."""
        if rule.startswith('!') or rule.startswith('['):
            return 'comment'

        elif rule.startswith(BLOCKING_SYMBOLS):
            return 'blocking'

        elif rule.startswith('@@'):
            return 'allow'

        # Exception rules
        elif '##' in rule and ':has(' in rule:
            return 'element_hiding_exception'

        # Element hiding rules
        elif '##' in rule:
            return 'element_hiding'

        # Domain blocking rules
        elif rule.startswith('||'):
            return 'domain_block'

        # URL patterns
        elif rule.startswith(('|http', '|https', '/', '*')):
            return 'url_pattern'
        else:
            return 'other'

    def process_rule_to_json(self, rule: str) -> None:
        """Process and categorize a single filter rule."""
        category = self.categorize(rule)

        if category == 'comment':
            return
        try:
            if category == 'blocking' or category == 'domain_block':
                parsed = self.parse_blocking_rules(rule)
                self.filters['blocking'].append(parsed)

            elif category == 'allow':
                parsed = self.parse_exception_rules(rule)
                self.filters['allow'].append(parsed)

            elif category == 'element_hiding':
                parsed = self.parse_element_hiding_rules(rule)
                self.filters['element_hiding'].append(parsed)

            elif category == 'other':
                parsed = self.parse_other_rules(rule)
                self.filters['other'].append(parsed)

        except Exception as e:
            print(f"Error processing rule: {rule} - {e}")
            return

    def parse_blocking_rules(self, rule) -> dict:
        """Parse a blocking rule into a regex pattern."""

        rule_holder = {
            'type': 'blocking',
            'pattern': '',
            'modifiers': {}
        }

        if rule.startswith(BLOCKING_SYMBOLS):
            rule = r".*" + rule.replace('.', '\\.').replace('?', '\\?').replace('*', '.*')
        elif rule.startswith('||'):
            rule_holder["type"] = "domain_block"
            if '^' in rule:
                rule_holder["pattern"] = (r"^(?:https?:\/\/)?(?:w\.?|ww\.?|www\.)?" + rule.split('||', 1)[1]
                                          .split('^')[0].replace('*', '.*'))
            else:
                rule_holder["pattern"] = (r"^(?:https?:\/\/)?(?:w\.?|ww\.?|www\.)?" + rule.split('||', 1)[1]
                                          .replace('*', '.*'))

            # return rule_holder
        modifier_part = None
        if '$' in rule:
            # if rule.count('$') > 1:
            #     rule = rule.replace("$", "", 1)
            if '^' in rule and '||' in rule and '*' in rule:
                pattern_part = rule_holder["pattern"] + r'.*' + re.escape(rule[2:].split('^*', 1)[1].split('$', 1)[0]) + r'.*'
                modifier_part = rule.split('$', 1)[1]
            elif '||' in rule and '*' in rule:
                pattern_part = rule.split('||', 1)[1].split('$', 1)[0].replace('*', '.*')
                modifier_part = rule.split('||', 1)[1].split('$', 1)[1]
            elif '||' in rule:
                pattern_part, modifier_part = rule.split('$', 1)
            else:
                pattern_part, modifier_part = rule.split('$', 1)
            rule_holder["pattern"] = pattern_part
        else:
            rule_holder["pattern"] = rule
        if modifier_part:
            modifiers = modifier_part.split(",")
            for mod in modifiers:
                if "=" in mod:
                    key, value = mod.split("=", 1)
                    if key == "domain":
                        rule_holder["modifiers"]["domain"] = {}
                        domains = value.split("|")
                        rule_holder["modifiers"]["domain"]["include"] = [d for d in domains if not d.startswith("~")]
                        rule_holder["modifiers"]["domain"]["exclude"] = [d[1:] for d in domains if d.startswith("~")]
                    else:
                        rule_holder["modifiers"][key] = value
                elif mod.startswith("~"):
                    rule_holder["modifiers"][mod[1:]] = False
                else:
                    rule_holder["modifiers"][mod] = True

        # if '|' in rule and not rule.startswith(('|', '||')) and not rule.endswith('|'):
        #     if 'domain' in rule.split('|')[0]:
        #         rule = f"||"
        #     rules = rule.split('|')
        # return
        return rule_holder

    def parse_other_rules(self, rule) -> dict:
        """Parse rules that don't fit the previous categories."""
        rule_holder = {
            'type': '',
            'pattern': '',
            'modifiers': {}
        }
        if rule.startswith('|') and not rule.startswith('||'):
            type_part, pattern_part = rule[1:].split(':', 1)
            if type_part == 'javascript':
                rule_holder['type'] = 'javascript_behavior'
                if '$' in pattern_part:
                    pattern_part, modifier_part = pattern_part.split('$', 1)
                    rule_holder['pattern'] = pattern_part
                    modifiers = modifier_part.split(',')
                    for mod in modifiers:
                        if '=' in mod:
                            key, value = mod.split('=', 1)
                            rule_holder['modifiers'][key] = value
                        else:
                            rule_holder['modifiers'][mod] = True
                else:
                    rule_holder['pattern'] = pattern_part
            else:
                rule_holder['type'] = type_part
                if '$' in rule:
                    pattern_part, modifier_part = pattern_part.split('$', 1)
                    rule_holder['pattern'] = pattern_part
                    modifiers = modifier_part.split(',')
                    for mod in modifiers:
                        if '=' in mod:
                            key, value = mod.split('=', 1)
                            if key == 'domain':
                                rule_holder['modifiers']['domain'] = {}
                                domains = value.split('|')
                                rule_holder['modifiers']['domain']['include'] = [d for d in domains if
                                                                                 not d.startswith("~")]
                                rule_holder['modifiers']['domain']['exclude'] = [d[1:] for d in domains if
                                                                                 d.startswith("~")]
                            else:
                                rule_holder['modifiers'][key] = value
                        else:
                            rule_holder['modifiers'][mod] = True

        return rule_holder

    def parse_exception_rules(self, rule) -> dict:
        """Parse exception rules."""
        rule_holder = {
            'type': 'allow',
            'pattern': '',
            'modifiers': {}
        }
        if rule.split('@@')[1].startswith('||'):
            rule = rule.split('||')[1]
            rule = r'.*' + rule.replace('.', '\\.').replace('?', '\\?').replace('*', '.*')
            if '$' in rule:
                pattern_part, modifier_part = rule.split('$', 1)
                rule_holder['pattern'] = pattern_part
                modifiers = modifier_part.split(',')
                for mod in modifiers:
                    if '=' in mod:
                        key, value = mod.split('=', 1)
                        if key == 'domain':
                            rule_holder['modifiers']['domain'] = {}
                            domains = value.split('|')
                            rule_holder['modifiers']['domain']['include'] = [d for d in domains if
                                                                             not d.startswith("~")]
                            rule_holder['modifiers']['domain']['exclude'] = [d[1:] for d in domains if
                                                                             d.startswith("~")]
                        else:
                            rule_holder['modifiers'][key] = value
                    elif mod.startswith('~'):
                        rule_holder['modifiers'][mod[1:]] = False
                    else:
                        rule_holder['modifiers'][mod] = True
        return rule_holder

    def parse_element_hiding_rules(self, rule) -> dict:
        """Parse element hiding exception rules."""
        rule_holder = {
            'type': 'element_hiding',
            'selector_type': '',
            'selector': '',
            'domain': '',
            'inner_elements': {}
        }
        if rule.startswith('##'):
            rule = rule.split('##')[1]
            if rule.startswith('#'):
                rule_holder['selector_type'] = 'id'
                if '>' in rule:
                    rule_holder['selector'] = rule.split('#')[1].split('>')[0]
                    rule_holder['inner_elements'] = {}  # would contain key:value|tag:attribute
                    inner_elements = rule.split('>')
                    for element in inner_elements:
                        if '[' in element and not element.startswith('['):
                            rule_holder['inner_elements'][element.split('[', 1)[0]] = element.split('[')[1].split(']')[
                                0]
                if '[' in rule and '>' not in rule.split("#")[1].split('[')[0]:
                    rule_holder['selector'] = rule.split('#')[1].split('[')[0]
                    rule_holder['inner_elements'] = {}
                    inner_elements = rule.split('[')
                    for element in inner_elements:
                        # TODO: Need to separate this afterwards
                        if "^=" in element:
                            if element.split("^=")[0] == 'style' and ";" in element.split("^=")[1]:
                                rule_holder['inner_elements']['style'] = [att[0].strip().replace('"', "") for att in
                                                                          [item.split(':') for item in element.split("^=")[1][1:-1]
                                                                          .split(";")[:-1]] if att != ""]
                            else:
                                rule_holder['inner_elements'][element.split("^=")[0]] = element.split("^=")[1][1:-1]
                        elif "=" in element:
                            if element.split("=")[0] == 'style' and ";" in element.split("=")[1]:
                                rule_holder['inner_elements']['style'] = [att[0].strip().replace('"', "") for att in
                                                                          [item.split(':') for item in element.split("=")[1][1:-1]
                                                                          .split(";")[:-1]] if att != ""]
                            else:
                                rule_holder['inner_elements'][element.split("=")[0]] = element.split("=")[1][1:-1]
                if '>' not in rule and "[" not in rule:
                    rule_holder['selector'] = rule.split('#')[1]
                    rule_holder['inner_elements'] = {}
            elif rule.startswith('.'):
                rule_holder['selector_type'] = 'class'
                if '>' in rule:
                    rule_holder['selector'] = rule.split('.')[1].split('>')[0]
                    rule_holder['inner_elements'] = {}
                    inner_elements = rule.split('>')
                    for element in inner_elements:
                        if '[' in element and not element.startswith('['):
                            rule_holder['inner_elements'][element.split('[', 1)[0]] = element.split('[')[1].split(']')[
                                0]
                if '[' in rule and '>' not in rule.split(".")[1].split('[')[0]:
                    rule_holder['selector'] = rule.split('.')[1].split('[')[0]
                    rule_holder['inner_elements'] = {}
                    inner_elements = rule.split('[')
                    for element in inner_elements:
                        # TODO: Need to separate this afterwards
                        if "^=" in element:
                            if element.split("^=")[0] == 'style' and ";" in element.split("^=")[1]:
                                rule_holder['inner_elements']['style'] = [att[0].strip().replace('"', "") for att in
                                                                          [item.split(':') for item in
                                                                           element.split("^=")[1][1:-1]
                                                                           .split(";")[:-1]] if att != ""]
                            else:
                                rule_holder['inner_elements'][element.split("^=")[0]] = element.split("^=")[1][1:-1]
                        elif "=" in element:
                            if element.split("=")[0] == 'style' and ";" in element.split("=")[1]:
                                rule_holder['inner_elements']['style'] = [att[0].strip().replace('"', "") for att in
                                                                          [item.split(':') for item in
                                                                           element.split("=")[1][1:-1]
                                                                           .split(";")[:-1]] if att != ""]
                            else:
                                rule_holder['inner_elements'][element.split("=")[0]] = element.split("=")[1][1:-1]
                if '>' not in rule and "[" not in rule:
                    rule_holder['selector'] = rule.split('.')[1]
                    rule_holder['inner_elements'] = {}

            # elif rule.startswith('['):
        return rule_holder



if __name__ == "__main__":
    main = EasyListFilters()
    main.parse()
    with open("rules.json", "w") as f:
        json.dump(main.filters, f, indent=4)
