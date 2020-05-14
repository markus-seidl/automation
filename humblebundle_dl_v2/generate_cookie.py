# Use this to generate cookies needed for the humblebundle-downloader

import time
import logging
from selenium import webdriver
from webdriverdownloader import GeckoDriverDownloader

logger = logging.getLogger(__name__)


def _get_cookie_str(driver):
    raw_cookies = driver.get_cookies()
    baked_cookies = ''
    for cookie in raw_cookies:
        baked_cookies += cookie['name'] + "=" + cookie['value'] + ";"
    # Remove the trailing ;
    return baked_cookies[:-1]


def generate_cookie(cookie_path):
    gdd = GeckoDriverDownloader()
    gecko_driver = gdd.download_and_install()

    # TODO: load previous cookies so it does not ask to re verify using an
    # email code each time
    driver = webdriver.Firefox(executable_path=gecko_driver[1])

    driver.get('https://www.humblebundle.com/login')

    while '/home/library' not in driver.current_url:
        # Waiting for the user to login
        time.sleep(.25)

    cookie_str = _get_cookie_str(driver)
    with open(cookie_path, 'w') as f:
        f.write(cookie_str)

    logger.info("Saved cookies to " + cookie_path)

    driver.quit()


if __name__ == "__main__":
    generate_cookie("./cookies.txt")
