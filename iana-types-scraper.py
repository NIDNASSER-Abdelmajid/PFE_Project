from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

import json


chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_services = ChromeDriverManager().install()

driver = webdriver.Chrome(service=Service(chrome_services), options=chrome_options)
driver.get("https://www.iana.org/assignments/media-types/media-types.xml")

# Wait for all the element with tag name "h2" to be present
elements = WebDriverWait(driver, 10).until(
    EC.presence_of_all_elements_located((By.TAG_NAME, "h2"))
)
types = dict()

for e in elements:
    if e.text == "example":
        continue
    table = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "table-"+e.text))
    )
    rows = WebDriverWait(table, 10).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "tr"))
    )
    for i, row in enumerate(rows):
        if i == 0:
            continue

        cell = row.find_elements(By.TAG_NAME, "td")[1]
        text = cell.text
        # Add the text to the list of types
        if e.text not in types:
            types[e.text] = []
        types[e.text].append(text)

with open("data_files\\IANA_TYPES.json", "w") as file:
    json.dump(types, file, indent=4)

