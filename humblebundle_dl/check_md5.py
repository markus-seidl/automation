import pickle
import os
from os import listdir
from os.path import isfile, join
import hashlib
import subprocess

OUTPUT_DIR = "/media/terra/MyBookEx/HB/"
CALIBRE_CMD = "/Applications/calibre.app/Contents/console.app/Contents/MacOS/calibredb"


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class DownloadLink:
    def __init__(self):
        self.humanName = None
        self.company = None
        self.md5 = None
        self.link = None
        self.bundle_name = None

    def get_bundle_name(self):
        return self.bundle_name.replace("(pay what you want and help charity)", "")

    def get_filename(self):
        return self.link.split('/')[-1].split('?')[0]

    def is_pdf(self):
        return self.get_filename().endswith('.pdf')

    def is_cbz(self):
        return self.get_filename().endswith('.cbz')


allfiles = [f for f in listdir(OUTPUT_DIR) if isfile(join(OUTPUT_DIR, f))]

books = dict()

for f in allfiles:
    if not f.endswith('.pickle'):
        continue

    info = None
    with open(OUTPUT_DIR + f) as handle:
        info = pickle.load(handle)

    if info.humanName not in books:
        books[info.humanName] = list()

    books[info.humanName].append(info)

for book in books:
    book_info = books[book]

    if len(book_info) == 0:
        continue

    for file in book_info:
        file_path = OUTPUT_DIR + file.get_filename()
        if not os.path.exists(file_path):
            # print file_path, "doesn't exist"
            # os.remove(file_path + ".pickle")
            continue

        md5sum = md5(file_path)
        if md5sum != file.md5:
            print(file.get_filename(), file.md5, md5sum)  # , file.company, file.link
            # os.remove(OUTPUT_DIR + "/" + file.get_filename())
            # os.remove(OUTPUT_DIR + "/" + file.get_filename() + ".pickle")
