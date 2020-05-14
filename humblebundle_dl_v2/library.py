import os
import sys
import json
import parsel
import logging
import requests

# base code copied and modified to fit from https://github.com/xtream1101/humblebundle-downloader
from helper import clean_type

logger = logging.getLogger(__name__)


def _clean_name(dirty_str):
    allowed_chars = (' ', '_', '.', '-', '[', ']')
    clean = []
    for c in dirty_str.replace('+', '_').replace(':', ' -'):
        if c.isalpha() or c.isdigit() or c in allowed_chars:
            clean.append(c)

    return "".join(clean).strip().rstrip('.')


class LibraryBundle:
    def __init__(self):
        self.order_id = None
        self.bundle_title = None
        self.product_list = list()  # LibraryProduct
        self.product_dict = dict()  # LibraryProduct


class LibraryProduct:
    def __init__(self):
        self.product_title = None
        self.producer = None
        self.unfiltered_product_title = None
        self.types = dict()  # LibraryProductType


class LibraryProductType:
    def __init__(self):
        self.product_title = None
        self.file_types = list()  # LibraryProductFileType
        self.file_types_dict = dict()  # LibraryProductFileType


class LibraryProductFileType:
    def __init__(self):
        self.type = None
        self.url = None
        self.url_filename = None
        self.ext = None
        self.sha1 = None
        self.file_size = None
        self.small = None
        self.md5 = None
        self.platform = None

    def relative_filename(self):
        return "./" + str(self.url_filename[0]).lower() + "/" + self.url_filename


class Library:

    def __init__(self, cookie_path):
        self.cookie_path = cookie_path
        self.progress_bar = False

        with open(self.cookie_path, 'r') as f:
            self.account_cookies = f.read().strip()

        self.purchase_keys = self._get_purchase_keys()

        # Unfortunately we can't just query the complete library and *then* start downloading,
        # as the download links expire. So this has to be done on-demand

    def query_purchase_key(self, order_id):
        order_url = 'https://www.humblebundle.com/api/v1/order/{order_id}?all_tpkds=true'.format(
            order_id=order_id)  # noqa: E501
        try:
            order_r = requests.get(order_url,
                                   headers={'cookie': self.account_cookies,
                                            'content-type': 'application/json',
                                            'content-encoding': 'gzip',
                                            })
        except Exception:
            logger.error("Failed to get order key {order_id}"
                         .format(order_id=order_id))
            return

        logger.debug("Order request: {order_r}".format(order_r=order_r))
        order = order_r.json()
        bundle_title = _clean_name(order['product']['human_name'])
        logger.info("Checking bundle: " + str(bundle_title))

        ret = LibraryBundle()
        ret.order_id = order_id
        ret.bundle_title = bundle_title
        ret.product_list = list()
        ret.product_dict = dict()

        for product in order['subproducts']:
            p = self.query_product(order_id, bundle_title, product)
            ret.product_dict[p.product_title] = p
            ret.product_list.append(p)

        return ret

    def query_product(self, order_id, bundle_title, product):
        unfiltered_product_title = str(product['human_name'])
        product_title = _clean_name(unfiltered_product_title)

        ret = LibraryProduct()
        ret.product_title = product_title
        ret.unfiltered_product_title = unfiltered_product_title
        ret.producer = product['payee']['human_name']

        # Get all types of download for a product
        for download_type in product['downloads']:

            product_type = LibraryProductType()
            product_type.platform = download_type['platform']
            ret.types[product_type.platform] = product_type

            # Download each file type of a product
            for file_type in download_type['download_struct']:

                product_file_type = LibraryProductFileType()

                try:
                    product_file_type.url = file_type['url']['web']
                except KeyError as ke:
                    logger.warning("No url found: {bundle_title}/{product_title}: {ke}."
                                   .format(bundle_title=bundle_title,
                                           product_title=product_title, ke=ke))
                    continue

                product_file_type.url_filename = product_file_type.url.split('?')[0].split('/')[-1]
                product_file_type.ext = product_file_type.url_filename.split('.')[-1]

                try:
                    product_file_type.type = clean_type(file_type['name']) if 'name' in file_type else None
                    product_file_type.sha1 = file_type['sha1'] if 'sha1' in file_type else None
                    product_file_type.file_size = file_type['file_size'] if 'file_size' in file_type else None
                    product_file_type.small = file_type['small'] if 'small' in file_type else None
                    product_file_type.md5 = file_type['md5'] if 'md5' in file_type else None
                except KeyError as ke:
                    logger.warning("A key wasn't found for: {ke}.".format(ke=ke))

                product_type.file_types.append(product_file_type)  # only add it if it has an url
                product_type.file_types_dict[product_file_type.type] = product_file_type
        return ret

    def download_product_file_type(self, p: LibraryProductFileType, output_dir):
        # logger.info("- Downloading {pt}".format(pt=p.type))

        dir = output_dir + "/" + str(p.url_filename[0]).lower()
        local_filename = dir + "/" + p.url_filename
        if not os.path.exists(dir):
            os.mkdir(dir)

        try:
            self._download_file(p.url, local_filename)

        except (Exception, KeyboardInterrupt) as e:
            # Do not overwrite the progress bar on next print
            if self.progress_bar:
                print()

            logger.error("Failed to download file {local_filename}"
                         .format(local_filename=local_filename))

            # Clean up broken downloaded file
            try:
                os.remove(local_filename)  # noqa: E701
            except OSError:
                pass  # noqa: E701

            if type(e).__name__ == 'KeyboardInterrupt':
                sys.exit()

    def _download_file(self, url, local_filename):
        # TODO fast bailout, remove after initial bulk download
        if os.path.exists(os.path.abspath(local_filename)):
            return

        try:
            logging.info("  - Requesting {url}".format(url=url))
            product_r = requests.get(url, stream=True)
        except Exception:
            logger.error("Failed to download {url}".format(url=url))
            return

        total_length = product_r.headers.get('content-length')
        if os.path.exists(os.path.abspath(local_filename)):
            if os.path.getsize(os.path.abspath(local_filename)) == int(total_length):
                logger.info(
                    "Local file {local_filename} is already fully downloaded".format(local_filename=local_filename))
                return
            else:
                os.remove(local_filename)
        logger.info("Downloading: {local_filename}".format(local_filename=local_filename))

        with open(local_filename, 'wb') as outfile:
            if total_length is None:  # no content length header
                outfile.write(product_r.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in product_r.iter_content(chunk_size=4096):
                    dl += len(data)
                    outfile.write(data)
                    pb_width = 50
                    done = int(pb_width * dl / total_length)
                    if self.progress_bar:
                        print("\t{percent}% [{filler}{space}]"
                              .format(local_filename=local_filename,
                                      percent=int(done * (100 / pb_width)),
                                      filler='=' * done,
                                      space=' ' * (pb_width - done),
                                      ), end='\r')

                if dl != total_length:
                    raise ValueError("Download did not complete")

    def _get_purchase_keys(self):
        try:
            library_r = requests.get('https://www.humblebundle.com/home/library',  # noqa: E501
                                     headers={'cookie': self.account_cookies})
        except Exception:
            logger.error("Failed to get list of purchases")
            return []

        logger.debug("Library request: " + str(library_r))
        library_page = parsel.Selector(text=library_r.text)
        orders_json = json.loads(library_page.css('#user-home-json-data')
                                 .xpath('string()').extract_first())
        return orders_json['gamekeys']
