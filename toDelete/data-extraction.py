import re
import json
from typing import Dict, List, Union


class ELFilterParser:
    @staticmethod
    def parse(filter_str: str) -> str:
        """Convert an Adblock Plus filter to a regex pattern with proper wildcard handling."""
        if not filter_str:
            return ".*"

        # Handle special exception cases first
        if filter_str.startswith("@@||") and "/" not in filter_str and "$" not in filter_str:
            domain = filter_str[4:].replace(".", r"\.")
            return f"^https?://([^/]+\\.)?{domain}(/|$)"

        result = filter_str

        # Step 1: Handle literal dots in domains and extensions
        # Escape dots in likely domains and file extensions
        result = re.sub(
            r'(^|\|)([a-z0-9-]+\.(?:com|org|net|gov|edu|co|uk|jp|de|fr|it|ru|info))(?=[^a-z]|$)',
            lambda m: m.group(1) + m.group(2).replace('.', r'\.'),
            result,
            flags=re.IGNORECASE
        )

        # Step 2: Handle literal dots in file extensions
        result = re.sub(
            r'\.(js|css|jpg|jpeg|png|gif|webp|svg|php|html?)(?=[^a-z]|$)',
            r'\.\1',
            result,
            flags=re.IGNORECASE
        )

        # Step 3: Escape other regex special characters (except dots and stars)
        special_chars = r'([?+^$(){}[\]|])'
        result = re.sub(special_chars, r'\\\1', result)

        # Step 4: Handle wildcards and anchors
        # Convert * to .* but don't double them
        result = result.replace('*', '.*')

        # Handle pattern-starting rules
        if result.startswith('||'):
            result = result[2:]
            result = f"^https?://(?:[^/]+\\.)?{result}"
        elif result.startswith('|'):
            result = result[1:]
            result = f"^{result}"

        # Handle pattern-ending rules
        if result.endswith('|'):
            result = result[:-1]
            result = f"{result}$"

        # Handle separator character
        result = result.replace('^', r'[^\w\d_%-]')

        # Step 5: Ensure proper wildcard handling for patterns like "-ad-manager/"
        # Add .* prefix if pattern starts with non-special character
        if not re.match(r'^[|@*^]', result):
            result = f".*{result}"

        # Add .* suffix if pattern doesn't end with special character
        if not re.search(r'[*|^]$', result):
            result = f"{result}.*"

        # Clean up any double .* patterns
        result = re.sub(r'(\.\*)+', '.*', result)

        return result


class EasyListCategorizer:
    def __init__(self):
        self.categories: Dict[str, List[Dict[str, Union[str, List[str]]]]] = {
            'domain_block': [],  # ||example.com
            'url_pattern': [],  # |https://example.com/ads
            'element_hiding': [],  # example.com##.ad
            'element_hiding_exception': [],  # @@||example.com##.ad
            'exception': [],  # @@|https://example.com
            'scriptlet_injection': [],  # example.com#%#scriptlet
            'document_exception': [],  # @@||example.com^$document
            'generichide': [],  # @@||example.com$generichide
            'genericblock': [],  # ||example.com$genericblock
            'csp': [],  # ||example.com$csp=
            'header': [],  # ||example.com$header=
            'redirect': [],  # ||example.com$redirect=
            'comment': [],  # ! Comment
            'other': []  # Unclassified
        }

    @staticmethod
    def categorize(rule: str) -> str:
        """Categorize the filter according to ABP syntax docs."""
        rule = rule.strip()

        if not rule or rule.startswith('!'):
            return 'comment'

        # Document exceptions and generichide
        if rule.startswith('@@||') and rule.endswith('$document'):
            return 'document_exception'
        if rule.startswith('@@||') and rule.endswith('$generichide'):
            return 'generichide'

        # Exceptions
        if rule.startswith('@@'):
            if '##' in rule:
                return 'element_hiding_exception'
            return 'exception'

        # Element hiding
        if '##' in rule:
            return 'element_hiding'

        # Scriptlet injection
        if '#%#' in rule or '$script' in rule:
            return 'scriptlet_injection'

        # Special filter options
        if '$' in rule:
            options = rule.split('$')[1].lower()
            if 'csp=' in options:
                return 'csp'
            if 'header=' in options:
                return 'header'
            if 'redirect' in options:
                return 'redirect'
            if 'genericblock' in options:
                return 'genericblock'

        # Domain-only patterns
        if rule.startswith('||') and '/' not in rule and '$' not in rule:
            return 'domain_block'

        # URL patterns
        if rule.startswith(('|http', '|https', '/', '*')):
            return 'url_pattern'

        return 'other'

    def process_rule(self, rule: str) -> None:
        """Process and categorize a single filter rule."""
        category = self.categorize(rule)

        if category == 'comment':
            self.categories[category].append({'raw': rule})
            return

        try:
            parsed = {
                'raw': rule,
                'regex': None,
                'options': None
            }

            if category in ['element_hiding', 'element_hiding_exception']:
                parts = rule.split('##')
                parsed['selector'] = parts[1]
                parsed['regex'] = ELFilterParser.parse(parts[0])
            elif '$' in rule:
                main_part, options = rule.split('$', 1)
                parsed['regex'] = ELFilterParser.parse(main_part)
                parsed['options'] = options.split(',')
            else:
                parsed['regex'] = ELFilterParser.parse(rule)

            self.categories[category].append(parsed)
        except Exception as e:
            self.categories['other'].append({
                'raw': rule,
                'error': str(e)
            })

    def to_json(self, filename: str) -> None:
        """Save categorized filters to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.categories, f, indent=2, ensure_ascii=False)

    @staticmethod
    def process_easylist(input_file: str, output_file: str) -> None:
        """Process an EasyList file and output categorized JSON."""
        categorizer = EasyListCategorizer()

        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    categorizer.process_rule(line)

        # Print statistics
        print("Filter categorization complete:")
        for category, rules in categorizer.categories.items():
            print(f"{category:>25}: {len(rules):>6} rules")

        # Save results
        categorizer.to_json(output_file)
        print(f"\nResults saved to {output_file}")

    def main(self):
        self.process_easylist("list_of_rules\\easylist.txt", "easylist_categorized.json")


if __name__ == "__main__":
    parser = EasyListCategorizer()
    parser.main()
