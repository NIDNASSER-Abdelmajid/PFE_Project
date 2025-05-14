import datetime
import hashlib
import json
import logging
import os
from time import sleep
from typing import Optional
from urllib.parse import urlparse
from tqdm import tqdm
import concurrent.futures
from threading import Lock

import requests
from selenium import webdriver
from selenium.common import NoSuchElementException, TimeoutException, NoAlertPresentException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC

from checker import TrackingChecker
from compareParsers import AdTester
from crawlerdb import crawler2db, Website
from settings import COOKIES_BUTTON_SELECTORS


class Crawler:
    """Web crawler for analyzing website ads and tracking elements."""

    def __init__(self, websites_path: str, analysis_type: str = None,max_retries: int = 3) -> None:
        """Initialize crawler with list of websites to analyze."""
        self.analysis_type = analysis_type
        self.websites = websites_path
        self.tracker_checker = TrackingChecker(json_file="data/rules_lists/parsed_rules/EasyPrivacy.json")
        self.driver = self._initialize_webdriver()
        self.max_retries = max_retries
        self.db = crawler2db()
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _initialize_webdriver() -> webdriver.Chrome:
        """Configure and return Chrome WebDriver instance with proper timeouts"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--enable-logging")
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--lang=en")

        chrome_options.set_capability("timeouts", {
            "pageLoad": 120000,
            "script": 30000
        })

        chrome_options.add_experimental_option(
            "prefs", {
                "profile.default_content_setting_values.cookies": 1,
                "profile.block_third_party_cookies": False
            }
        )

        service = Service(
            ChromeDriverManager().install(),
            service_args=['--verbose'],
            log_path='chromedriver.log'
        )

        driver = webdriver.Chrome(
            service=service,
            options=chrome_options
        )

        driver.set_page_load_timeout(120)
        driver.set_script_timeout(30)

        return driver

    def accept_cookies(self) -> bool:
        """Attempt to accept cookies using predefined selectors."""
        try:
            WebDriverWait(self.driver, 20).until(
                EC.any_of(
                    *[EC.presence_of_element_located((selector["by"], selector["value"]))
                      for selector in COOKIES_BUTTON_SELECTORS]
                )
            )
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            for selector in COOKIES_BUTTON_SELECTORS:
                try:
                    button = self.driver.find_element(selector["by"], selector["value"])
                    if button.is_displayed():
                        button.click()
                        return True
                except NoSuchElementException:
                    continue
            return False
        except TimeoutException:
            return False

    def get_all_cookies(self, url: str, wait_time: int = 0) -> None:
        """Capture and categorize cookies from target URL."""
        driver = self.driver
        cookies = {"first_party": [], "third_party": []}

        driver.execute_cdp_cmd("Network.enable", {})
        driver.get(url)

        domain = urlparse(url).netloc
        allowed_domains = [f'.{domain}', f'.www.{domain}', f'www.{domain}']

        sleep(wait_time)
        raw_cookies = driver.execute_cdp_cmd('Network.getAllCookies', {})
        website_id = self.db.add_website(domain=domain)

        for cookie in raw_cookies['cookies']:
            if ('sameSite' in cookie and
                    cookie['sameSite'] == 'None' and
                    cookie['domain'] not in allowed_domains):
                cookies['third_party'].append(cookie)
                self.db.store_cookies(
                    website_id=website_id,
                    cookies=cookies['third_party'],
                    party='third'
                )
            else:
                cookies['first_party'].append(cookie)
                self.db.store_cookies(
                    website_id=website_id,
                    cookies=cookies['first_party'],
                    party='first'
                )

        print(f"Cookies saved successfully for \"{domain}\".")

    def get_logs(self, url: str,  website_id: int) -> None:
        """Capture and save network performance logs."""
        domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
        logs = self.driver.get_log("performance")
        data = []

        for log in [json.loads(entry["message"])["message"] for entry in logs if entry]:
            if log["method"] == "Network.requestWillBeSent":
                data.append(log)
                self.db.add_request(
                    website_id=website_id,
                    request_id=log["params"]["requestId"],
                    url=log["params"]["request"]["url"],
                    method=log["params"]["request"]["method"],
                    resource_type=log["params"]["type"],
                    timestamp=datetime.datetime.fromtimestamp(
                        log["params"].get("wallTime", 0),
                        datetime.timezone.utc
                    ),
                )
            elif log["method"] == "Network.responseReceived":
                data.append(log)
                self.db.add_response(
                    request_id=log["params"]["requestId"],
                    status_code=log["params"]["response"]["status"],
                    headers=log["params"]["response"]["headers"],
                    security_state=log["params"]["response"].get("securityState", "insecure"),
                    timestamp=datetime.datetime.fromtimestamp(
                        log["params"]["response"].get("responseTime", 0) / 1000,
                        datetime.timezone.utc
                    ),
                )

        os.makedirs(f"data/websites_data/{domain}", exist_ok=True)
        with open(f"data/websites_data/{domain}/network_log.json", "w") as f:
            json.dump(data, f, indent=2)
        print(f"{len(data)} logs saved successfully.")

    def handle_popups(self, timeout: int = 5) -> bool:
        """Detect and close all popup types (alerts, modals, new windows, iframes)."""
        original_window = self.driver.current_window_handle
        popups_found = False

        try:
            alert = self.driver.switch_to.alert
            alert.accept()
            popups_found = True
        except NoAlertPresentException:
            pass

        if len(self.driver.window_handles) > 1:
            for handle in self.driver.window_handles:
                if handle != original_window:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
                    print("Closed a popup window")
                    popups_found = True
            self.driver.switch_to.window(original_window)

        modal_selectors = [
            'div[class*="modal"]',
            'div[class*="popup"]',
            'div[class*="cookie"]',
            'div[class*="consent"]',
            'div[role="dialog"]'
        ]
        for selector in modal_selectors:
            try:
                modal = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                )
                self.driver.execute_script("arguments[0].remove()", modal)
                popups_found = True
            except (NoSuchElementException, TimeoutException):
                continue

        try:
            iframes = self.driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="popup"], iframe[src*="modal"]')
            for iframe in iframes:
                self.driver.switch_to.frame(iframe)
                self.driver.switch_to.default_content()
                popups_found = True
        except Exception as e:
            logging.error(f"Error handling iframe popups: {e}")
            self.driver.switch_to.default_content()

        return popups_found

    @staticmethod
    def is_third_party(request_url: str, page_url: str) -> bool:
        """Check if a request URL is a third-party request relative to a page URL."""

        def get_origin(url: str) -> str:
            """Extract the origin (scheme + netloc) from a URL."""
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"

        return get_origin(request_url) != get_origin(page_url)

    def media_downloader(self, url: str, website_id: int) -> None:
        """Download media assets with proper response_id handling"""
        domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
        log_path = f"data/websites_data/{domain}/network_log.json"

        if not os.path.exists(log_path):
            logging.warning(f"No network logs found at {log_path}")
            return

        with open(log_path, "r") as f:
            logs = json.load(f)

        for entry in logs:
            if entry["method"] != "Network.responseReceived":
                continue

            asset_url = entry["params"]["response"]["url"]
            asset_type = entry["params"]["type"].lower()
            request_id = entry["params"]["requestId"]
            response_id = request_id

            with open(f"data/websites_data/{domain}/Successful_urls.txt", "a+") as f:
                f.write(f"{asset_url}:::{asset_type}:::{request_id}\n")

            if asset_type not in ['image', 'media'] or asset_url.startswith(("blob", "data")):
                continue

            try:
                response = requests.get(asset_url, stream=True, timeout=10)
                response.raise_for_status()

                save_dir = f"data/websites_data/{domain}/responseReceived/{asset_type}s"
                os.makedirs(save_dir, exist_ok=True)

                filename = os.path.basename(urlparse(asset_url).path)
                if not filename:
                    filename = f"asset_{hash(asset_url)}"

                file_path = os.path.join(save_dir, filename)
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)

                self.db.add_downloaded_file(
                    website_id=website_id,
                    request_id=request_id,
                    response_id=response_id,
                    file_type=asset_type,
                    file_path=file_path
                )

            except Exception as e:
                logging.error(f"Failed to download {asset_url} - {e}")
                with open(f"data/websites_data/{domain}/Failed_urls.txt", "a") as f:
                    f.write(f"{asset_url}\n")

    @staticmethod
    def read_urls_from_file(file_path: str) -> list[str]:
        """Read URLs from text file."""
        with open(file_path, "r") as f:
            return [line.strip() for line in f if line.strip()]

    def start_crawling(self) -> None:
        """Execute full crawling workflow with enhanced error handling and retries."""
        logging.info("================ Crawler Started ================")
        urls = self.read_urls_from_file(self.websites)

        for url in urls:
            url, category = url.split(" ::: ")
            if not self._validate_url(url):
                logging.warning(f"Skipping invalid URL: {url}")
                continue

            domain = urlparse(url).netloc
            website_id = None
            attempts = 0
            success = False

            while attempts < self.max_retries and not success:
                attempts += 1
                try:
                    website_id = self._get_or_create_website(domain, category)
                    if not website_id:
                        continue

                    self._process_website(url, website_id)
                    success = True

                except WebDriverException as e:
                    logging.error(f"WebDriver error (attempt {attempts}/{self.max_retries}) for {url}: {str(e)}")
                    if attempts == self.max_retries:
                        self._mark_website_failed(website_id)
                    sleep(5)

                except Exception as e:
                    logging.error(f"Unexpected error processing {url}: {str(e)}")
                    self._mark_website_failed(website_id)
                    break

                finally:
                    if self.driver:
                        try:
                            self.driver.quit()
                        except Exception as e:
                            logging.error(f"Error quitting driver: {str(e)}")

                    logging.info(f"Finished processing {url} (attempt {attempts})")
            self.db.close()
        logging.info("================ Crawler Finished ================")

    def _process_website(self, url: str, website_id: int) -> None:
        """Process a single website with all crawling steps."""
        self.driver = self._initialize_webdriver()
        print(f"Processing {url}")
        self.driver.get(url)
        sleep(5)

        domain_safe = urlparse(url).netloc.replace("www.", "").replace(".", "_")
        os.makedirs(f"data/websites_data/{domain_safe}", exist_ok=True)
        self.driver.save_screenshot(f"data/websites_data/{domain_safe}/screenshot.png")

        is_popup = self.handle_popups()
        self.accept_cookies()

        self.get_logs(url, website_id)
        self.media_downloader(url, website_id)
        self.get_all_cookies(url, 20)
        self._analyze_assets_for_ads_and_trackers(domain_safe, url, is_popup)

        self._mark_website_completed(website_id)

    def _get_or_create_website(self, domain: str, category: str) -> Optional[int]:
        """Get existing website ID or create new entry"""
        try:
            return self.db.add_website(domain=domain, category=category)
        except Exception as e:
            logging.error(f"Database error for {domain}: {e}")
            return None

    def _mark_website_completed(self, website_id: int) -> None:
        """Update website status to complete."""
        try:
            website = self.db.session.query(Website).get(website_id)
            if website:
                website.visited_status = "completed"
                self.db.session.commit()
        except Exception as e:
            logging.error(f"Error marking website completed: {str(e)}")

    def _mark_website_failed(self, website_id: int) -> None:
        """Update website status to failed."""
        try:
            website = self.db.session.query(Website).get(website_id)
            if website:
                website.visited_status = "failed"
                self.db.session.commit()
        except Exception as e:
            logging.error(f"Error marking website failed: {str(e)}")

    @staticmethod
    def _validate_url(url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception as e:
            logging.error(f"Invalid URL {url}: {str(e)}")
            return False


    def _analyze_assets_for_ads_and_trackers(self, domain: str, url: str, is_popup: bool) -> None:
        success_file = f"data/websites_data/{domain}/Successful_urls.txt"
        if not os.path.exists(success_file):
            return

        with open(success_file, "r") as f:
            assets = [line.strip().split(':::') for line in f if line.strip()]

        ads_results_path = f"data/websites_data/{domain}/ads_results.txt"
        trackers_results_path = f"data/websites_data/{domain}/trackers_results.txt"
        results_lock = Lock()
        db_lock = Lock()
        ad_tester = AdTester()
        # domain_fn = domain.replace("www.", "").replace(".", "_")

        def save_result(path, result, asset_url):
            with results_lock:
                with open(path, "a") as file:
                    file.write(f"[{result}] {asset_url}\n")

        def save_ad_resource(asset_url, max_retries=3):
            try:
                base_dir = f"data/websites_data/{domain}/ADs"
                os.makedirs(base_dir, exist_ok=True)

                url_path = urlparse(asset_url).path
                ext = os.path.splitext(url_path)[1] or '.png'
                file_hash = hashlib.md5(asset_url.encode()).hexdigest()
                filename = f"AD_{file_hash}{ext}"
                filepath = os.path.join(base_dir, filename)

                for attempt in range(max_retries + 1):
                    try:
                        with requests.get(asset_url, stream=True, timeout=10) as response:
                            response.raise_for_status()
                            with open(filepath, "wb") as f:
                                for chunk in response.iter_content(1024):
                                    f.write(chunk)
                        return True
                    except requests.exceptions.RequestException as e:
                        if attempt == max_retries:
                            raise
                        logging.warning(f"Attempt {attempt + 1} failed for {asset_url}, retrying...")
                        return None
                return None

            except Exception as e:
                logging.warning(f"Failed to save AD resource {asset_url}: {str(e)}")
                os.makedirs(f"data/websites_data/{domain}", exist_ok=True)
                with open(f"data/websites_data/{domain}/Failed_ADs.txt", "a") as f:
                    f.write(f"{asset_url}\n")
                return False

        def update_db(request_id, rule_id, decision):
            with db_lock:
                self.db.add_analysis_result(
                    request_id=request_id,
                    rule_id=rule_id,
                    decision=decision
                )

        def analyze_tracker(asset_url, asset_type, is_popup, url):
            is_third_party = self.is_third_party(asset_url, url)
            test_params = {
                "type": asset_type.lower(),
                "popup": is_popup,
                "third-party": is_third_party
            }
            is_tracker = self.tracker_checker.is_tracker(asset_url, test_params)
            tracker_result = "TRACKER" if is_tracker[0] else "NOT TRACKER"
            return is_tracker, tracker_result, test_params

        def analyze_ad(asset_url, test_params, ad_tester):
            is_ad = ad_tester.test_url(asset_url, test_params)
            ad_result = "AD" if is_ad[0] or is_ad[1] else "NOT AD"
            return is_ad, ad_result

        def process_asset(asset, pbar):
            asset_url, asset_type, request_id = asset
            try:
                is_tracker, tracker_result, test_params = analyze_tracker(asset_url, asset_type, is_popup, url)
                save_result(trackers_results_path, tracker_result, asset_url)

                is_ad = (False, False, None)
                ad_result = "NOT AD"
                if not is_tracker[0]:
                    is_ad, ad_result = analyze_ad(asset_url, test_params, ad_tester)
                    save_result(ads_results_path, ad_result, asset_url)
                    if ad_result == "AD" and asset_type in ["image", "media"]:
                        save_ad_resource(asset_url)
                else:
                    save_result(ads_results_path, ad_result, asset_url)

                rule_id = is_ad[2] if not is_tracker[0] else is_tracker[1]
                decision = self._determine_ad_decision(is_ad, is_tracker)
                update_db(request_id, rule_id, decision)

                if len(asset_url) > 30:
                    pbar.set_postfix_str(f"Current: {asset_url[:30]}...")
                else:
                    pbar.set_postfix_str(f"Current: {asset_url}")

                return True
            except Exception as e:
                logging.error(f"Error analyzing {asset_url}: {str(e)}")
                return False
            finally:
                pbar.update(1)

        max_workers = min(32, (os.cpu_count() or 1) * 4)
        with tqdm(total=len(assets),
                  desc=f"Analyzing {domain}",
                  unit="asset",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(executor.map(lambda asset: process_asset(asset, pbar), assets))


    @staticmethod
    def _determine_ad_decision(is_ad: tuple, is_tracker) -> str:
        """Determine the final ad decision based on test results."""
        if is_tracker[0]:
            return "TRACKER"
        elif is_ad[0] or is_ad[1]:
            return "AD"
        return "SAFE"
