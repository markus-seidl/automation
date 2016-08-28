# To install the Python client library:
# pip install -U selenium

# Import the Selenium 2 namespace (aka "webdriver")
import keyring
from selenium.common.exceptions import ElementNotVisibleException
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
import os
import glob
import time
import urllib2
import cPickle


# Configuration part
OUTPUT_DIR = "/Volumes/Leviathan/HB/"
HB_USER = keyring.get_password("humblebundle_dl", "user")
HB_PASS = keyring.get_password("humblebundle_dl", "pass")
# /Configuration part


# Handle initial keyring setup
if HB_USER is None:
    HB_USER = raw_input("username:")

if HB_PASS is None:
    HB_PASS = raw_input("password:")

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

    def get_filename(self):
        return self.link.split('/')[-1].split('?')[0]


def login(d):
    d.get('https://www.humblebundle.com/home/library')

    # Select the Python language option
    input_email = d.find_element_by_id("account-login-username")
    input_password = d.find_element_by_id("account-login-password")

    input_email.send_keys(HB_USER)
    input_password.send_keys(HB_PASS)

    d.find_element_by_class_name ("js-submit").click()

    print("Wait until user has entered security code...")
    time.sleep(30)


def load_all_purchases(d):
    # Navigate to purchases and get all purchases links
    d.get('https://www.humblebundle.com/home/purchases')

    # Find max pages for purchases
    page_navigator = d.find_elements_by_class_name('jump-to-page')
    page_navigator = page_navigator[-2]

    max_pages = int(page_navigator.text)

    purchases = list()

    for page in range(0, max_pages):
        for purchase_row in d.find_elements_by_class_name('row'):
            purchases.append(purchase_row.get_attribute('href'))

        page_navigator = d.find_elements_by_class_name('jump-to-page')
        page_navigator[-1].click()

    return purchases


def parse_purchase_page(d, purchase):
    d.get(purchase)

    links = list()

    for row in d.find_elements_by_class_name('row'):
        productName = row.get_attribute('data-human-name')
        company = row.find_element_by_class_name('subtitle').find_element_by_tag_name('a').text

        product = Product()
        product.humanName = productName
        product.company = company
        links.append(product)

        for platform in row.find_elements_by_class_name('downloads'):

            # TODO find out platform name
            platform_name = platform.get_attribute('class')
            platform_name = str(platform_name).replace("js-platform downloads", "")
            platform_name = str(platform_name).replace("show", "")
            platform_name = str(platform_name).replace(" ", "")

            if platform_name not in product.downloads:
                product.downloads[platform_name] = list()

            for dl_link in platform.find_elements_by_class_name('download'):
                download = DownloadLink()

                link = dl_link.find_element_by_class_name('a')
                download.md5 = dl_link.get_attribute('data-md5')
                download.link = link.get_attribute('href')
                download.humanName = productName
                download.platformName = platform_name
                download.purchaseLink = purchase
                download.company = company
                product.downloads[platform_name].append(download)

    return links


def download_link(dl):
    file_name = OUTPUT_DIR + dl.get_filename()
    file_name_pickle = file_name + ".pickle"

    # the pickle file may exist, but not the download. This is ok, as import_calibre removes the download after import
    # to save disk space and mark the file as "imported"
    if os.path.exists(file_name_pickle):
        print "File already exists: ", file_name
        return

    if not os.path.exists(file_name):
        u = urllib2.urlopen(dl.link)
        with open(file_name, 'wb') as f:
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            print "Downloading: %s Bytes: %s" % (file_name, file_size)

            file_size_dl = 0
            block_sz = 8192
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break

                file_size_dl += len(buffer)
                f.write(buffer)
                # status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                # status = status + chr(8)*(len(status)+1)
                # print status,

    with open(file_name_pickle, "wb") as handle:
        cPickle.dump(dl, handle)


login(driver)

purchases = load_all_purchases(driver)

for purchase in purchases:
    products = parse_purchase_page(driver, purchase)

    for product in products:
        for platform in product.downloads:

            if platform != 'ebook':
                continue

            for download in product.downloads[platform]:

                if "zip" in download.link:
                    continue

                download_link(download)
