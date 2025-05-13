from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_domain_category(drive, url):
    URL = f"https://sitelookup.mcafee.com/en/feedback/url?action=checksingle&url={url}"

    drive.get(URL)
    try:
        WebDriverWait(drive, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[3]/div[2]/div[2]/div/div/div/div[2]/div["
                                                      "1]/div/form[1]/table/tbody/tr[4]/td/div/input"))
        ).click()
        element = WebDriverWait(drive, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[3]/div[2]/div[2]/div/div/div/div[2]/div["
                                                      "1]/div/form[2]/table/tbody/tr[2]/td[4]"))
        )
    except Exception as e:
        print(f"Error waiting for element: {e}")
        return None

    return [cat.strip() for cat in element.text.replace("-", "").split("\n")]


if __name__ == "__main__":
    driver = webdriver.Chrome()
    print("Starting categorization process...")
    websites_path = "data/websites/websites.txt"
    with open(websites_path, "r+") as f:
        websites = f.readlines()
        f.close()
    with open("data/websites/websites_categorized.txt", "w+") as f:
        for website in websites:
            website = website.strip()
            category = get_domain_category(driver, website)
            f.write(f"{website} ::: {','.join(category)}\n")
        f.close()