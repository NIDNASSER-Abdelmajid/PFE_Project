import os
# from typing import Dict, List
from settings import ESSENTIAL_DIRS, RULES_LISTS
from support import rule_list_downloader
from checker import ELParser
from crawler import Crawler


class WebAnalyzer:
    def __init__(self):
        self._initialize_project_structure()
        self.parser = ELParser()

    def run(self):
        """Main execution flow"""
        self._download_and_parse_rules()
        self._crawl_websites()
        print("All tasks completed successfully!")

    @staticmethod
    def _initialize_project_structure():
        """Create all required directories"""
        for dir_path in ESSENTIAL_DIRS.values():
            os.makedirs(dir_path, exist_ok=True)
        print("Project directories initialized")

    def _download_and_parse_rules(self):
        """Handle rule downloading and parsing"""
        print("Downloading rule lists...")
        rule_list_downloader(RULES_LISTS)

        print("Parsing rules...")
        for rules_list in RULES_LISTS.keys():
            rules_path = os.path.join("data", "rules_lists", "Lists", f"{rules_list}.txt")
            with open(rules_path, "r", encoding="utf-8") as f:
                self.parser.parse_rules(f.readlines())
                output_path = os.path.join(ESSENTIAL_DIRS["parsed_rules"], f"{rules_list}.json")
                self.parser.save_to_json(output_path)
        print(f"Processed {len(RULES_LISTS)} rules lists")

    @staticmethod
    def _crawl_websites():
        """Execute website crawling"""
        print("Starting website crawling...")
        websites_path = os.path.join(ESSENTIAL_DIRS["websites"], "websites_categorized.txt")
        crawler = Crawler(websites_path)
        crawler.start_crawling()


if __name__ == "__main__":
    try:
        analyzer = WebAnalyzer()
        analyzer.run()
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
        raise
