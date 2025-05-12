from selenium.webdriver.common.by import By


ESSENTIAL_DIRS = {
    "lists": "data\\rules_lists\\lists",
    "parsed_rules": "data\\rules_lists\\parsed_rules",
    "websites": "data\\websites",
}

COOKIES_BUTTON_SELECTORS = [
    {"by": By.ID, "value": "acceptAll"},
    {"by": By.ID, "value": "consent-accept"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Accept')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Agree')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Consent')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Allow')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'I accept')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'OK')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Accept all')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'accept all')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Accept All')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'I agree')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Continue')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Yes')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'X')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Yes, I accept')]"},
    {"by": By.XPATH, "value": "//button[contains(text(), 'Confirm My Choices')]"},
    {"by": By.XPATH, "value": "//a[contains(text(), 'Agree and Proceed')]"},
    {"by": By.XPATH, "value": "//button[contains(@class, 'accept-btn')]"},
    {"by": By.XPATH, "value": "//a[contains(@class, 'btn_yes') and @href='#' and @role='button']"},
    {"by": By.XPATH, "value": "//a[contains(@class, 'cookies-button')]"},
    {"by": By.XPATH, "value": "//button[contains(@id, 'accept') or contains(@id, 'agree')]"},
    {"by": By.XPATH, "value": "//button[@aria-label='Yes, I accept']"},
    {"by": By.XPATH, "value": "//button[@aria-label='accept-cookies']"},
    {"by": By.XPATH, "value": "//button[@aria-label='Accept cookies']"},
    {"by": By.XPATH, "value": "//button[@aria-label='Accept all cookies']"},
    {"by": By.XPATH, "value": "//button[@aria-label='I accept cookies']"},
    {"by": By.XPATH, "value": "//button[@aria-label='I agree to the use of cookies']"},
    {"by": By.XPATH, "value": "//button[@aria-label='Agree']"},
    {"by": By.XPATH, "value": "//button[@aria-label='OK']"},
    {"by": By.XPATH, "value": "//button[@aria-label='Continue']"},
    {"by": By.XPATH, "value": "//button[@aria-label='Yes']"},
    {"by": By.XPATH, "value": "//button[@aria-label='Accept']"},
]

RULES_LISTS = {
    "EasyList": {
        "description": "Primary list for blocking ads (banners, pop-ups, video ads)",
        "url": "https://easylist.to/easylist/easylist.txt"
    },
    "EasyPrivacy": {
        "description": "Blocks tracking scripts and analytics (Google Analytics, Facebook Pixel)",
        "url": "https://easylist.to/easylist/easyprivacy.txt"
    },
}

__all__ = [
    "COOKIES_BUTTON_SELECTORS",
    "RULES_LISTS",
    "ESSENTIAL_DIRS",
]
