# To install the Python client library:
# pip install -U selenium

# Import the Selenium 2 namespace (aka "webdriver")
import keyring
from selenium.common.exceptions import ElementNotVisibleException
from selenium import webdriver
from selenium.webdriver.support.select import Select
import os
import glob
import time

# Configuration part
OUTPUT_DIR = "/Users/msei/Downloads/Audible/"
AUDIBLE_USER = keyring.get_password("audible_dl", "user")
AUDIBLE_PASS = keyring.get_password("audible_dl", "pass")
# /Configuration part

##########

# Handle initial keyring setup
if AUDIBLE_USER is None:
    AUDIBLE_USER = raw_input("Audible username:")

if AUDIBLE_PASS is None:
    AUDIBLE_PASS = raw_input("Audible password:")

keyring.set_password("audible_dl", "user", AUDIBLE_USER)
keyring.set_password("audible_dl", "pass", AUDIBLE_PASS)

# Downloads
profile = webdriver.FirefoxProfile()
profile.set_preference("browser.download.folderList", 2)
profile.set_preference("browser.download.manager.showWhenStarting", "false")
profile.set_preference("browser.download.dir", OUTPUT_DIR)
profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "audio/vnd.audible.aax")

# Firefox
driver = webdriver.Firefox(firefox_profile=profile)


def login(d):
    d.get('http://audible.de/sign-in')

    # Select the Python language option
    input_email = d.find_element_by_id("ap_email")
    input_password = d.find_element_by_id("ap_password")

    input_email.send_keys(AUDIBLE_USER)
    input_password.send_keys(AUDIBLE_PASS)

    d.find_element_by_id("signInSubmit").click()

    print("Wait until next page is loaded...")
    time.sleep(3)


def exists_part_file(output_dir):
    files = glob.glob(output_dir + os.sep + "*.part")
    if len(files) == 0:
        return None
    return files[0]

login(driver)

# Configure Library
driver.get("https://www.audible.de/lib")
select_lib_range = Select(driver.find_element_by_id("adbl_time_filter"))
select_lib_range.select_by_index(5)

time.sleep(4)

for i in range(0, 50):
    download_buttons = driver.find_elements_by_class_name("adbl-download-it")
    for db in download_buttons:
        name = db.get_attribute("title")
        info_file = name.replace("#", "").replace("-", "").replace("(", "").replace(")", "")
        if os.path.exists(OUTPUT_DIR + os.sep + info_file):
            print("Already downloaded: " + name)
            continue

        print("Download " + name)
        try:
            db.click()
        except ElementNotVisibleException:
            print("Failed (ElementNotVisibleException)")
            continue

        part_file = exists_part_file(OUTPUT_DIR)
        while not exists_part_file(OUTPUT_DIR) is None:
            time.sleep(1)

        open(OUTPUT_DIR + os.sep + info_file, 'w').close()

    next_links = driver.find_elements_by_class_name("adbl-page-next")
    next_link = next_links[0]
    next_link.click()

    time.sleep(2)



# Close the browser!
# driver.quit()
