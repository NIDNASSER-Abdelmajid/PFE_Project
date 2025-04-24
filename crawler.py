import itertools
import json
import os
import re
from time import sleep

from settings import *
from support import *

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class Crawler:
    """A class to crawl."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def webdriver_setup() -> Options:
        """Set up the Chrome WebDriver with desired options."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--enable-logging")
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--start-maximized")

        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.cookies": 1,
            "profile.block_third_party_cookies": False,
        })
        return chrome_options

    def driver_setup(self) -> webdriver.Chrome:
        """Set up the Chrome WebDriver with desired options."""
        chrome_options = self.webdriver_setup()
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        return driver

    def get_all_cookies(self, url, wait_time=0) -> None:
        """Get all the cookies from a website X"""

        # Set up logging preferences
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.webdriver_setup())
        cookies = {
            "first_party": [],
            "third_party": []
        }
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.get(url)
            url = url.split("//")[1]
            url = url.split(".", 1)[1] if "www." in url else url
            allowed_cookies_domain = ['.' + url, '.www.' + url, 'www.'+url]
            url = url.replace(".", "_")
            sleep(wait_time)
            raw_cookies = driver.execute_cdp_cmd('Network.getAllCookies', {})
            # Filter cookies into first-party and third-party
            for cookie in raw_cookies['cookies']:
                if ('sameSite' in cookie
                        and cookie['sameSite'] == 'None'
                        and cookie['domain'] not in allowed_cookies_domain):
                    cookies['third_party'].append(cookie)
                else:
                    cookies['first_party'].append(cookie)
            os.makedirs(f"data\\{url}\\cookies", exist_ok=True)
            with open(f"data\\{url}\\cookies\\{url}_cookies.json", "w") as file:
                json.dump(cookies, file, indent=4)
        except Exception as e:
            print(f"Exception: {e}")
        finally:
            driver.quit()

    @staticmethod
    def get_logs(driver: webdriver) -> None:
        """retrieve logs."""
        try:
            logs = driver.get_log("performance")
            with open("temp\\network_log.json", "w+") as f3:
                data = []
                for entry in logs:
                    log = json.loads(entry["message"])["message"]
                    if (
                            "Network.response" in log["method"]
                            or "Network.request" in log["method"]
                            or "Network.webSocket" in log["method"]
                    ):
                        data.append(log)
                f3.write(json.dumps(data, indent=2) + '\n')
                f3.close()
        except Exception as e:
            print(f'Error getting the logs: {e}')

        return

    @staticmethod
    def files_downloader(url: str) -> None:
        """Downloads and stores url of the downloadable files in the network"""
        url = url.split("//")[1].replace(".", "_")
        with open("temp\\network_log.json", "r+") as f:
            logs = json.load(f)
            f.close()
        for entry in logs:
            sleep(2)
            if entry["method"] == "Network.requestWillBeSent":
                _url = entry["params"]["request"]["url"]
                _type = entry["params"]["type"]
                print(f"URL: {_url}", f"Type: {_type}", end="\n\n")
                # download file if it is a downloadable file
                if _type in ["Stylesheet", "Image", "Script", "Document"]:
                    try:
                        file = requests.get(_url, stream=True)
                        _directory = f"temp\\downloads\\{url}\\requestWillBeSent\\{_type}s"
                        os.makedirs(_directory, exist_ok=True)
                        (open(_directory + f"\\{_url.split('/')[-1].split('?')[0]}", mode="wb")
                         .write(file.content))
                        open(f"temp\\downloads\\{url}\\Successful_urls.txt", mode="a+").write(_url + "\n")

                    except Exception as e:
                        print(f"Error downloading {_url}: {e}")
            elif entry["method"] == "Network.responseReceived":
                _url = entry["params"]["response"]["url"]
                _type = entry["params"]["type"]
                print(f"URL: {_url}", f"Type: {_type}", end="\n\n")
                # download file if it is a downloadable file
                if _type in ["Stylesheet", "Image", "Script", "Document"]:
                    try:
                        file = requests.get(_url, stream=True)
                        _directory = f"temp\\downloads\\{url}\\responseReceived\\{_type}s"
                        os.makedirs(_directory, exist_ok=True)
                        (open(_directory + f"\\{_url.split('/')[-1].split('?')[0]}", mode="wb")
                         .write(file.content))
                        open(f"temp\\downloads\\{url}\\Successful_urls.txt", mode="a+").write(_url + "\n")

                    except Exception as e:
                        print(f"Error downloading {_url}: {e}")

    @staticmethod
    def url_checker2(_url_sample, rules_json):
        __rules = rules_json["blocking"]
        domains_restriction = {}
        available_types = ['stylesheet', 'image', 'document', 'script']
        for rule in __rules:
            _arguments = []
            __arg, _res = None, None
            for _arg in rule.get('modifiers', {}):
                if _arg not in ['domain', 'image']:
                    _arguments.append((_arg, rule['modifiers'][_arg]))
                elif _arg == 'image':
                    _arguments.append(('image', rule['modifiers'][_arg]))
                elif _arg == "domain":
                    domains_restriction['include'] = rule['modifiers']['domain']['include'] if (
                        rule)['modifiers']['domain']['include'] else []
                    domains_restriction['exclude'] = rule['modifiers']['domain']['exclude'] if (
                        rule)['modifiers']['domain']['exclude'] else []

            url = re.search(r"(?:https?://)?(?:www\.)?([^/]+\.[a-zA-Z]{2,3})(?:$|/)", _url_sample).group(1)
            try:
                block_domain, keep_domain = url in domains_restriction['include'], url in domains_restriction['exclude']
            except:
                block_domain, keep_domain = 0, 0
            # if 'image' and _arguments in _arguments:
            #     img = [i for i in FORMAT_CONVERTER['image']]
            targeted_types = list(
                itertools.chain(*[FORMAT_CONVERTER[s[0]] for s in _arguments if s[1] and s[0] in available_types]))
            untargeted_types = list(
                itertools.chain(*[FORMAT_CONVERTER[s[0]] for s in _arguments if not s[1] and s[0] in available_types]))

            ut = '(' + '|'.join(targeted_types) + ')' if targeted_types else ''
            tt = '(?!' + '|'.join(untargeted_types) + ')' if untargeted_types else ''
            if targeted_types or untargeted_types:
                # print(targeted_types, untargeted_types, sep='----------\n-------------')
                pattern = r"{}.*\.{}{}(?:\?.*|$)".format(
                    rule["pattern"],
                    tt,
                    ut
                )
            else:
                pattern = rule["pattern"]
            # print(pattern)
            # print(__arg, _res, targeted_types, untargeted_types, sep="\n----------\n")
            __arg = re.search(pattern, _url_sample)
            _res = re.search(rule["pattern"], _url_sample)
            # print(domains_restriction)
            # print(url)
            if __arg or _res:
                # print('done!')
                if keep_domain:
                    # print("safe domain!")
                    return False
                else:
                    # print("succeeded!")
                    print(rule)
                    return True

            # print(rule)
            # input("Click Enter to Continue...")
        return None

    @staticmethod
    def read_urls_from_file(file_path):
        with open(file_path, "r") as file:
            urls = [line.strip() for line in file if line.strip()]
        return urls

    def main(self):
        print('--main--')
        urls = self.read_urls_from_file("data_files\\websites_demo")
        for url in urls:
            driver = self.driver_setup()
            driver.get(url)
            self.get_logs(driver)
            self.files_downloader(url)
            self.get_all_cookies(url, 20)

            with open("temp/downloads/www_bbc_com/Successful_urls.txt", "r") as f:
                links = f.readlines()
            with open(f"temp\\results.txt", 'a+') as f:
                for link in links:
                    res = self.url_checker2(link.replace('\n', ''), json_loader("rules.json"))
                    if res is None:
                        f.write("[NOT AD] " + url)
                        print("[NOT AD] " + url)
                    elif res:
                        f.write("[AD] " + url)
                        print("[AD] " + url)
                    else:
                        f.write("[SAFE DOMAIN] " + url)
                        print("[SAFE DOMAIN] " + url)
                f.close()
        print('----------------End-main-------------------')


if __name__ == "__main__":
    crawler = Crawler()
    crawler.main()



"""
Example of websites to use:
bbc.com
forbes.com
youtube.com

"""