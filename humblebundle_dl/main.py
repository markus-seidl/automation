# To install the Python client library:
# pip install -U selenium
# Download geckodriver and put into venv/bin https://github.com/mozilla/geckodriver/releases

# Import the Selenium 2 namespace (aka "webdriver")
import keyring
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import ElementNotVisibleException
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
import os
import glob
import time
import urllib.request, urllib.error, urllib.parse
import pickle


# Configuration part
OUTPUT_DIR = "/Volumes/Leviathan/HB/"
HB_USER = keyring.get_password("humblebundle_dl", "user")
HB_PASS = keyring.get_password("humblebundle_dl", "pass")
# /Configuration part


# Handle initial keyring setup
if HB_USER is None:
    HB_USER = input("username:")

if HB_PASS is None:
    HB_PASS = input("password:")

keyring.set_password("humblebundle_dl", "user", HB_USER)
keyring.set_password("humblebundle_dl", "pass", HB_PASS)

# https://ftp.mozilla.org/pub/firefox/releases/44.0/mac/en-US/
# Downloads
# profile = webdriver.Chrome()  # .FirefoxProfile()
# profile.set_preference("browser.download.folderList", 2)
# profile.set_preference("browser.download.manager.showWhenStarting", "false")
# profile.set_preference("browser.download.dir", OUTPUT_DIR)
# profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "audio/vnd.audible.aax")

# Firefox
driver = webdriver.Firefox()  # (firefox_profile=profile)


class Product:
    def __init__(self):
        self.purchasePage = None
        self.humanName = None
        self.downloads = dict()


class DownloadLink:
    def __init__(self):
        self.humanName = None
        self.md5 = None
        self.link = None
        self.company = None
        self.company_link = None
        self.bundle_name = None

    def get_filename(self):
        return self.link.split('/')[-1].split('?')[0]


def login(d):
    d.get('https://www.humblebundle.com/home/library')

    # Select the Python language option
    input_email = d.find_element_by_name("username")
    input_password = d.find_element_by_name("password")

    input_email.send_keys(HB_USER)
    input_password.send_keys(HB_PASS)

    time.sleep(5)

    input_password.submit()

    print("Wait until user has entered security code...")
    input('Press enter when done.')


def load_all_purchases(d):
    # Navigate to purchases and get all purchases links
    d.get('https://www.humblebundle.com/home/purchases')

    time.sleep(5)  # be sure that the js has executed completly (?)

    # Find max pages for purchases
    page_navigator = d.find_elements_by_class_name('jump-to-page')
    page_navigator = page_navigator[-2]

    max_pages = int(page_navigator.text)
    print("Detected pages " + str(max_pages))

    purchases = list()

    for page in range(0, max_pages):
        for purchase_row in d.find_elements_by_class_name('row'):
            link = 'https://www.humblebundle.com/downloads?key=' + purchase_row.get_attribute('data-hb-gamekey')
            purchases.append(link)

        page_navigator = d.find_elements_by_class_name('jump-to-page')

        hbd = False
        while not hbd:
            try:
                page_navigator[-1].click()
                hbd = True
            except ElementClickInterceptedException:
                hbd = False

    return purchases


def parse_purchase_page(d, purchase):
    d.get(purchase)
    print("*", "Examing page " + purchase)

    while len(d.find_elements_by_class_name('js-unclaimed-purchases-loading')) > 0:
        print("*", "AJAX Loading on page, waiting...")
        time.sleep(10)

    links = dict()
    page_title = d.title
    if page_title is None or page_title == "" or len(page_title) == 0:
        print("-")

    for wb in d.find_elements_by_class_name('whitebox-redux'):
        for platform in wb.find_elements_by_class_name('dlplatform-list'):
            platform_name = platform.text  # get_attribute('data-platform') doesn't seem to be there atm

            for row in wb.find_elements_by_class_name('row'):
                product_name = row.get_attribute('data-human-name')

                temp = row.find_element_by_class_name('subtitle')
                temp = temp.find_elements_by_tag_name('a')
                company = None
                company_link = None
                if len(temp) > 0:
                    company_link = temp[0].get_attribute('href')
                    company = temp[0].text

                product = None
                if product_name in links:
                    product = links[product_name]
                else:
                    product = Product()
                    links[product_name] = product
                    product.humanName = product_name
                    product.company = company
                    product.company_link = company_link

                for dl_link in row.find_elements_by_class_name('download'):
                    download = DownloadLink()

                    link = dl_link.find_element_by_class_name('a')
                    # download.md5 = dl_link.get_attribute('data-md5')
                    download.link = link.get_attribute('href')
                    download.humanName = product_name
                    download.platformName = platform_name
                    download.purchaseLink = purchase
                    download.company = company
                    download.company_link = company_link
                    download.bundle_name = page_title

                    if platform_name not in product.downloads:
                        product.downloads[platform_name] = list()

                    product.downloads[platform_name].append(download)

    return links


def download_link(dl):
    file_name = OUTPUT_DIR + dl.get_filename()
    file_name_pickle = file_name + ".pickle"

    # the pickle file may exist, but not the download. This is ok, as import_calibre removes the download after import
    # to save disk space and mark the file as "imported"
    # if os.path.exists(file_name_pickle):
    #     print "File already exists: ", file_name
    #     return

    if not os.path.exists(file_name):
        try:
            u = urllib.request.urlopen(dl.link)
            with open(file_name, 'wb') as f:
                meta = u.info()
                file_size = int(meta["Content-Length"])
                print("Downloading: %s %3.2f MB" % (file_name, file_size / 1024.0 / 1024.0))

                file_size_dl = 0
                last_report = 0
                block_sz = 8192
                print("\t", end=' ')
                while True:
                    buffer = u.read(block_sz)
                    if not buffer:
                        break

                    file_size_dl += len(buffer)
                    f.write(buffer)
                    p = file_size_dl * 100. / file_size
                    if p - last_report >= 10:
                        status = r"[%3.2f%%]" % (file_size_dl * 100. / file_size)
                        # status = status + chr(8)*(len(status)+1)
                        print(status, end=' ')
                        last_report = p
            print("...done")
        except urllib.error.HTTPError as e:
            print("Error while downloading " + dl.link)
            print(e)

    with open(file_name_pickle, "wb") as handle:
        pickle.dump(dl, handle)


login(driver)

purchases = load_all_purchases(driver)

i = 0
for purchase in purchases:
    i += 1
    products = parse_purchase_page(driver, purchase)
    print("Handle purchase page ", i, " of ", len(purchases), ": ", purchase)

    for product_name in products:
        product = products[product_name]
        for platform in product.downloads:

            if platform.lower() != 'ebook':
                continue

            for download in product.downloads[platform]:

                if "zip" in download.link:
                    continue

                file_name = OUTPUT_DIR + download.get_filename()
                file_name_pickle = file_name + ".pickle"

                with open(file_name_pickle, "wb") as handle:
                    pickle.dump(download, handle)

                if os.path.exists(file_name_pickle) and os.path.exists(file_name):
                    continue

                # print(" ", "*", "wget", "\"" + download.link + "\"", " -O ", file_name)

                download_link(download)
