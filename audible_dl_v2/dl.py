#!/usr/bin/env python3
import jsons
import logging
import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from tqdm import tqdm
import requests
import math
import audible_dl_v2.utils as utils

from urllib.parse import urlencode
from optparse import OptionParser


# find activation bytes via https://github.com/inAudible-NG/audible-activator
# plex audible scrapper https://github.com/macr0dev/Audiobooks.bundle


def create_driver(download_dir):
    opts = webdriver.ChromeOptions()
    # opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko")
    chrome_prefs = {
        "profile.default_content_settings.popups": "0",
        "download.default_directory": download_dir
    }
    opts.add_experimental_option("prefs", chrome_prefs)

    if sys.platform == 'win32':
        chromedriver_path = "chromedriver.exe"
    elif os.path.isfile("/usr/lib/chromium-browser/chromedriver"):  # Ubuntu package chromedriver path
        chromedriver_path = "/usr/lib/chromium-browser/chromedriver"
    elif os.path.isfile("/usr/local/bin/chromedriver"):  # macOS + Homebrew
        chromedriver_path = "/usr/local/bin/chromedriver"
    else:
        chromedriver_path = "./chromedriver"

    return webdriver.Chrome(options=opts,
                            executable_path=chromedriver_path)


def login(driver, username, password):
    base_url = 'https://www.audible.de/'
    sign_in_class = 'ui-it-sign-in-link'

    driver.get(base_url)

    sign_in_link = driver.find_element_by_class_name(sign_in_class)
    sign_in_link.click()

    search_box = driver.find_element_by_id('ap_email')
    search_box.send_keys(username)
    search_box = driver.find_element_by_id('ap_password')
    search_box.send_keys(password)
    search_box.submit()

    input("Press Enter after successful login.")


def switch_to_page(driver, page):
    logger.debug("Switching to page %s..." % page)
    driver.get(page)
    logger.debug("...done.")


def find_pages(driver):
    switch_to_page(driver, "https://www.audible.de/lib")  # move to the library page

    maxpage = 1
    for link in driver.find_elements_by_xpath("//a[@data-name ='page']"):
        maxpage = max(maxpage, int(link.text))

    logger.info("Found %s pages of books" % maxpage)

    ret = list()
    for i in range(1, maxpage + 1):
        ret.append("https://www.audible.de/lib?page=%i" % i)

    return ret


def find_downloads_on_page(driver, page):
    switch_to_page(driver, page)

    books = driver.find_elements_by_css_selector("[id^=adbl-library-content-row-]")

    ret = list()

    for book in books:
        # get all columns
        columns = book.find_elements_by_class_name('bc-table-column')

        # 0 = Image
        # 1 = Title
        # 2 = Author
        # 3 = Time
        # 4 = date of purchase
        # 5 = ratings
        # 6 = already downloaded
        # 7 = download link

        # title image
        title_image_link = columns[0].find_element_by_css_selector("[data-bc-hires^='https://m.media-amazon.com']")
        title_image = title_image_link.get_attribute("data-bc-hires")

        # Series ASIN
        series_asin_elements = columns[1].find_elements_by_css_selector("[href^='series?asin=']")
        series_asin = None
        if len(series_asin_elements) > 0:
            series_asin_element = series_asin_elements[0]
            series_asin = str(series_asin_element.get_attribute('href')) \
                .replace("https://www.audible.de/series?asin=", "")

        # author - title
        title_link = columns[1].find_element_by_css_selector("[href*='/pd/']")
        title = title_link.text
        author = columns[2].text

        # download link
        download_link = columns[7].find_element_by_css_selector("[href^='https://cds.audible.de']")
        dl_link = download_link.get_attribute('href')

        # asin
        asin_element = columns[0].find_element_by_css_selector("[name='asin']")
        asin = asin_element.get_attribute("value")

        ret.append(utils.Book(title, author, dl_link, title_image, asin, series_asin))

    return ret


def download_file(url, output_file):
    # with urllib.request.urlopen(url) as response, open(output_file, 'wb') as out_file:
    #     shutil.copyfileobj(response, out_file)

    if os.path.exists(output_file):
        logger.info("File %s already exists, skipping download." % output_file)
        return

    logger.info("Downloading %s" % output_file)

    # Streaming, so we can iterate over the response.
    r = requests.get(url, stream=True)

    # Total size in bytes.
    total_size = int(r.headers.get('content-length', 0))
    block_size = 1024

    wrote = 0
    with open(output_file, 'wb') as f:
        for data in tqdm(r.iter_content(block_size),
                         total=math.ceil(total_size // block_size),
                         unit='MB',
                         unit_scale=True):
            wrote = wrote + len(data)
            f.write(data)

    if total_size != 0 and wrote != total_size:
        logger.error("ERROR, something went wrong. Deleting file.")
        os.remove(output_file)

    logger.info("Download %s complete" % output_file)


def create_filename(book):
    author = str(book.author)
    if "," in author:
        author = author[:author.index(",")]

    author = author.replace(":", "").replace("\n", "").replace("?", "")
    title = book.title.replace(":", "").replace("\n", "").replace("?", "")

    return author + " - " + title


def fetch_chapters(driver, book):
    cloudplayer_url = "https://www.audible.de/cloudplayer?asin=%s" % book.asin
    switch_to_page(driver, cloudplayer_url)

    # find token
    token_element = driver.find_element_by_css_selector("[name='token']")
    token = token_element.get_attribute('value')

    js_1 = """
        fetch("https://www.audible.de/contentlicenseajax", {"credentials":"include","headers":{
        "accept":"application/json, text/javascript, */*; q=0.01","content-type":
        "application/x-www-form-urlencoded; charset=UTF-8"},"body":
    """

    params = dict()
    params['asin'] = book.asin
    params['token'] = token
    params['key'] = "AudibleCloudPlayer"
    params['action'] = "getUrl"
    js_2 = '"' + urlencode(params) + '"'

    js_3 = """
        ,"method":"POST","mode":"cors"}).then(response => { response.json().then(d => { window.blah = d }) } );
        return window.blah;
    """

    js = js_1 + js_2 + js_3
    driver.execute_script(js)

    time.sleep(2)  # lazy way to ensure the request has finished TODO check if window.blah exists.

    val = driver.execute_script("return window.blah")

    return val


def create_logger():
    global logger
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def create_cmd_line_parser():
    parser = OptionParser(usage="Usage: %prog [options]", version="%prog 0.2")
    parser.add_option("--username",
                      action="store",
                      dest="username",
                      default=False,
                      help="Audible username, use along with the --password option")
    parser.add_option("--password",
                      action="store",
                      dest="password",
                      default=False,
                      help="Audible password")
    parser.add_option("--directory",
                      action="store",
                      dest="directory",
                      default="./dl/",
                      help="Output directory")
    return parser


def download_chapters(out, driver, book):
    chapter_file_name = out + ".chapters"
    if os.path.exists(chapter_file_name):
        logger.info("File %s already exists, skipping download." % chapter_file_name)
        return

    chapters = fetch_chapters(driver, book)
    with open(chapter_file_name, 'w+') as f:
        f.write(jsons.dumps(chapters))


def download_series_information(out, driver, book):
    if book.series_asin is None:
        return  # no series

    series_file = out + "/" + book.series_asin + ".series_info"
    if os.path.exists(series_file):
        logger.info("File %s already exists, skipping download." % series_file)
        return

    switch_to_page(driver, "https://www.audible.de/series?asin=%s" % book.series_asin)

    # We are switching to that page, but the page will be garbled, if there is no series.

    series = list()
    i = 0
    while True:
        content = driver.find_element_by_id('center-4')
        elements = content.find_elements_by_class_name('productListItem')

        if len(elements) == 0:
            break

        for series_element in elements:
            subtitle = text_or_none(series_element, By.CLASS_NAME, 'subtitle')
            authorLabel = text_or_none(series_element, By.CLASS_NAME, 'authorLabel', 'Autor: ')
            narratorLabel = text_or_none(series_element, By.CLASS_NAME, 'narratorLabel', 'Sprecher: ')
            runtimeLabel = text_or_none(series_element, By.CLASS_NAME, 'runtimeLabel', 'Spieldauer: ')
            title = series_element.get_attribute('aria-label')

            asin_element = series_element.find_elements_by_css_selector("[data-trigger^='product-list-flyout-']")
            asin = None
            if len(asin_element) == 0:
                logger.warning("Unable to find asin for title %s. This title can't be correctly assigned." % title)
            else:
                asin = asin_element[0].get_attribute('data-trigger').replace("product-list-flyout-", "")

            series.append(utils.SeriesElement(asin, title, subtitle, authorLabel, narratorLabel, runtimeLabel))

        # are there more pages?
        # next_link = driver.find_elements_by_xpath("//button[@data-name ='page']")
        next_link = driver.find_elements_by_class_name('nextButton')
        if len(next_link) == 0:
            break

        if "bc-button-disabled" in next_link[0].get_attribute("class"):
            break

        next_link[0].click()
        time.sleep(2)

        i += 1
        if i > 100:
            logger.error("Searched 100 pages of one series, giving up.")
            break

    with open(series_file, 'w+') as f:
        f.write(jsons.dumps(series))


def text_or_none(source, by, name, strip_text=None):
    elements = source.find_elements(by=by, value=name)
    if len(elements) == 0:
        return None

    ret = elements[0].text
    if strip_text:
        ret = ret.replace(strip_text, "")

    return ret


def save_book_object(out, book):
    filename = out + ".bookinfo"
    if os.path.exists(filename):
        logger.info("File %s already exists, skipping download." % filename)
    else:
        with open(filename, 'w+') as f:
            f.write(jsons.dumps(book))


def find_book_language(driver, book):
    switch_to_page(driver, "https://www.audible.de/pd/%s" % book.asin)

    language_elements = driver.find_elements_by_class_name('languageLabel')
    if len(language_elements) == 0:
        logger.warning("Can't find language for %s, voice recognition will be done with default language" % book.asin)
        return

    language = language_elements[0].text.replace('Sprache: ', '').strip()
    book.language = language


if __name__ == "__main__":
    create_logger()
    cmd_line_parser = create_cmd_line_parser()
    (options, args) = cmd_line_parser.parse_args()

    # Start
    output_dir = os.path.abspath(options.directory) + "/"
    with create_driver(output_dir) as d:
        login(d, options.username, options.password)

        pages = find_pages(d)

        for page in pages:
            books = find_downloads_on_page(d, page)

            for book in books:
                out = output_dir + create_filename(book)

                download_file(book.title_image, out + ".jpg")
                download_chapters(out, d, book)
                download_series_information(output_dir, d, book)
                find_book_language(d, book)
                save_book_object(out, book)

                download_file(book.dl_link, out + ".aax")
