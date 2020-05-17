# Uses calibre-server to import the books into the calibre database
import pickle
import os
import base64
import json
import logging
import time
import requests

from helper import all_metainf_files, clean_type
from library import LibraryProduct, LibraryProductType, LibraryProductFileType

DOWNLOAD_DIR = "/Volumes/Adrastea/dl"
SERVER_URL = "http://localhost:8080"
SLEEP = 10  # let calibre breath between requests

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)
logger = logging.getLogger(__name__)


def find_import_files_in_product(product: LibraryProduct) -> [LibraryProductFileType]:
    files = list()
    for type in product.types:
        pt = product.types[type]
        for file in pt.file_types:
            local_filename = os.path.join(DOWNLOAD_DIR, file.relative_filename())
            if os.path.exists(local_filename):
                files.append(file)

    return files


def find_type_in_list(list: [LibraryProductFileType], type: str) -> LibraryProductFileType:
    for t in list:
        if clean_type(t.type) == type:
            return t
    return None


def import_product(product: LibraryProduct):
    files = find_import_files_in_product(product)

    if len(files) == 0:
        logger.warning("Empty product: " + product.product_title)
        return

    logger.info("Handling product: {name}".format(name=product.unfiltered_product_title))
    first = None
    first_format = None
    preferred_format_order = ["MOBI", "EPUB"]
    preferred_format_order_i = 0
    while first is None:
        first_format = preferred_format_order[preferred_format_order_i]
        first = find_type_in_list(files, first_format)

        preferred_format_order_i += 1
        if preferred_format_order_i >= len(preferred_format_order):
            break

    if first is None:
        first = files[0]

    ret = cdb_add_book(0, 'n', first.url_filename, None, os.path.join(DOWNLOAD_DIR, first.relative_filename()))
    if 'book_id' not in ret:
        logger.warning("  - Book was already imported, skipping")
        return
    book_id = ret['book_id']
    logger.info("  - Calibre imported the book as id {id} with the title {title} from format {ext}".format(
        id=book_id,
        title=ret['title'],
        ext=first.ext
    ))
    first_format = clean_type(first.type)
    if first_format == "PDF":
        # PDF titles are the worst, update it with the one we know
        logger.info("  - Setting title to {title} and marking the book with 'check_metadata'".format(
            title=product.unfiltered_product_title
        ))
        set_title(book_id, product.unfiltered_product_title)
        set_tag(book_id, "check_metadata")

    for file in files:
        if file.type == first_format:
            continue

        logger.info("  - Adding format {ext}".format(ext=file.ext))
        add_format(ret['book_id'], file.url_filename, file.ext, os.path.join(DOWNLOAD_DIR, file.relative_filename()))


def set_tag(book_id, new_tag, library_id=None):
    body = dict()
    body['changes'] = dict()
    body['loaded_book_ids'] = list()
    body['loaded_book_ids'].append(book_id)
    body['all_dirtied'] = False
    body['changes']['tags'] = new_tag

    library_id = "" if library_id is None else library_id
    url = "{root}/cdb/set-fields/{book_id}/{library_id}".format(
        root=SERVER_URL,
        book_id=book_id,
        library_id=library_id
    )
    time.sleep(SLEEP / 1000.0)
    ret = requests.post(url, json=body)

    if ret.status_code != 200:
        raise Exception("Error from calibre " + str(ret.content))
    return ret.json()


def set_title(book_id, new_title, library_id=None):
    body = dict()
    body['changes'] = dict()
    body['loaded_book_ids'] = list()
    body['loaded_book_ids'].append(book_id)
    body['all_dirtied'] = False
    body['changes']['title'] = new_title

    library_id = "" if library_id is None else library_id
    url = "{root}/cdb/set-fields/{book_id}/{library_id}".format(
        root=SERVER_URL,
        book_id=book_id,
        library_id=library_id
    )
    time.sleep(SLEEP / 1000.0)
    ret = requests.post(url, json=body)

    if ret.status_code != 200:
        raise Exception("Error from calibre " + str(ret.content))
    return ret.json()


def add_format(book_id, filename, ext, local_file, library_id=None):
    body = dict()
    body['changes'] = dict()
    body['loaded_book_ids'] = list()
    body['loaded_book_ids'].append(book_id)
    body['all_dirtied'] = False
    body['changes']['added_formats'] = list()
    nf = dict()
    body['changes']['added_formats'].append(nf)
    nf['ext'] = ext
    nf['data_url'] = 'unused,'

    with open(local_file, 'rb') as f2:
        data = f2.read()
    nf['data_url'] += base64.b64encode(data).decode('ascii')

    library_id = "" if library_id is None else library_id
    url = "{root}/cdb/set-fields/{book_id}/{library_id}".format(
        root=SERVER_URL,
        book_id=book_id,
        library_id=library_id
    )
    time.sleep(SLEEP / 1000.0)
    ret = requests.post(url, json=body)

    if ret.status_code != 200:
        raise Exception("Error from calibre " + str(ret.content))
    return ret.json()


def cdb_add_book(job_id, add_duplicates, filename, library_id, local_file):
    with open(local_file, 'rb') as f1:
        library_id = "" if library_id is None else library_id
        url = "{root}/cdb/add-book/{job_id}/{add_duplicates}/{filename}/{library_id}".format(
            root=SERVER_URL,
            job_id=job_id,
            add_duplicates=add_duplicates,
            filename=filename,
            library_id=library_id
        )
        ret = requests.post(url, data=f1)
        time.sleep(SLEEP / 1000.0)
        if ret.status_code != 200:
            raise Exception("Error from calibre " + ret.content)
        return ret.json()


if __name__ == "__main__":
    all_infs = all_metainf_files(DOWNLOAD_DIR)

    for info in all_infs:
        with open(info, 'rb') as info:
            product = pickle.load(info)

        import_product(product)
