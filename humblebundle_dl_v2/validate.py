from library import Library, LibraryProductType, LibraryProduct, LibraryProductFileType
from helper import all_metainf_files
from multiprocessing import Process
from multiprocessing import Pool
import logging
import os
import pickle
import glob

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)
logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "/Volumes/Adrastea/dl"


def check_product(p: LibraryProduct):
    for type in p.types:
        check_type(p.product_title, p.types[type])


def check_type(product_title, product_type: LibraryProductType):
    exists = dict()
    for ft in product_type.file_types:
        exists[ft.type] = check_file_type(ft)

    exists_str = ""
    if "PDF (HQ)" in exists:
        if exists["PDF (HQ)"]:
            exists_str += "PDF [X] "
        else:
            exists_str += "PDF [ ] "
    elif "PDF" in exists:
        if exists["PDF"]:
            exists_str += "PDF [X] "
        else:
            exists_str += "PDF [ ] "

    for product_type in ["EPUB", "MOBI", "CBZ"]:
        if product_type in exists:
            if exists[product_type]:
                exists_str += product_type + " [X] "
            else:
                exists_str += product_type + " [ ] "

    logger.info("- {product_title}: {exists_str}".format(product_title=product_title, exists_str=exists_str))


def check_file_type(ft: LibraryProductFileType):
    file = DOWNLOAD_DIR + "/" + str(ft.url_filename[0]).lower() + "/" + ft.url_filename
    return os.path.exists(file)


if __name__ == "__main__":
    all_infs = all_metainf_files(DOWNLOAD_DIR)

    for info in all_infs:
        with open(info, 'rb') as f:
            product = pickle.load(f)

        check_product(product)
