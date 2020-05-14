from library import Library, LibraryProductType, LibraryProduct
from multiprocessing import Process
from multiprocessing import Pool
import logging
import os
import pickle

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
)
logger = logging.getLogger(__name__)


def ensure_meta_info(product: LibraryProduct, product_type: LibraryProductType):
    if len(product_type.file_types) == 0:
        logging.warning("Couldn't determine meta info for {name}".format(name=product_type.product_title))
        return

    type = product_type.file_types[0]
    file_name = type.url_filename[0:-len(type.ext) - 1]

    dir = download_dir + "/" + str(file_name[0]).lower()
    local_filename = dir + "/" + file_name + ".metainf"
    if not os.path.exists(dir):
        os.mkdir(dir)

    if os.path.exists(local_filename):  # TODO remove
        return

    with open(local_filename, 'w+b') as f:
        pickle.dump(product, f)


def download_product(product):
    logger.info("## " + product.product_title)

    unfiltered = False
    first_type = None
    for type in product.types:
        product_type = product.types[type]
        if first_type is None:
            first_type = product_type

        file_types = ""
        for f in product_type.file_types:
            file_types += f.type + ", "
        logger.info("- Available types: " + file_types)

        if "PDF (HQ)" in product_type.file_types_dict:
            l.download_product_file_type(product_type.file_types_dict["PDF (HQ)"], download_dir)
            unfiltered = True
        elif "PDF" in product_type.file_types_dict:
            l.download_product_file_type(product_type.file_types_dict["PDF"], download_dir)
            unfiltered = True

        for type in ["EPUB", "MOBI", "CBZ"]:
            if type in product_type.file_types_dict:
                l.download_product_file_type(product_type.file_types_dict[type], download_dir)
                unfiltered = True

    if unfiltered:  # this is already downloaded or was downloaded
        # Use the first type to get the filename, ignoring all other types. Might cause problems with non-books...
        ensure_meta_info(product, first_type)


if __name__ == "__main__":
    cookie_path = "./cookies.txt"
    download_dir = "/Volumes/Adrastea/dl"

    l = Library(cookie_path)

    i = 0
    for purchase in l.purchase_keys:
        bundle = l.query_purchase_key(purchase)

        logger.info("# Handle purchase {bundle_title} {i}/{len}".format(bundle_title=bundle.bundle_title, i=i,
                                                                        len=len(l.purchase_keys)))
        if True:
            with Pool(5) as p:
                p.map(download_product, bundle.product_list)

            if len(bundle.product_list) == 0:
                logger.error("Empty bundle {purchase_key}".format(purchase_key=purchase))

        else:
            for product in bundle.product_list:
                download_product(product)

        i += 1
