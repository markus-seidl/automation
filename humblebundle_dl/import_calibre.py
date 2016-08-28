import cPickle
import os
from os import listdir
from os.path import isfile, join
import subprocess

OUTPUT_DIR = "/Users/msei/Downloads/HB/"
CALIBRE_CMD = "/Applications/calibre.app/Contents/console.app/Contents/MacOS/calibredb"


class DownloadLink:
    def __init__(self):
        self.humanName = None
        self.company = None
        self.md5 = None
        self.link = None

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
        info = cPickle.load(handle)

    if info.humanName not in books:
        books[info.humanName] = list()

    books[info.humanName].append(info)

for book in books:
    book_info = books[book]

    if len(book_info) == 0:
        continue

    # If one file is missing this either means there is an error (which can always happen in scripts ;) ) or we already
    # have imported one format. The code below would create duplicate entries in this case, so we skip this book
    can_import = 0
    for file in book_info:
        if not os.path.exists(OUTPUT_DIR + file.get_filename()):
            can_import += 1

    if can_import > 0:
        print book, "Can't be imported " + str(can_import) + " files are missing from " + str(len(book_info))

    print book
    cmd = list()
    cmd.append(CALIBRE_CMD)
    cmd.append("add")
    # cmd.append("--empty")
    cmd.append("--title")
    cmd.append(book_info[0].humanName)
    cmd.append("--tags")
    cmd.append("HUMBLE_BUNDLE")
    cmd.append("--languages")
    cmd.append("en")
    cmd.append(OUTPUT_DIR + book_info[0].get_filename())

    calibre_output = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE).stdout.read()
    book_id = -1
    try:
        book_id = int(calibre_output.split('\n')[1].replace("Added book ids: ", ""))
    except:
        print calibre_output
        continue

    for file in book_info:
        cmd = list()
        cmd.append(CALIBRE_CMD)
        cmd.append("add_format")
        cmd.append("--dont-replace")
        cmd.append(str(book_id))
        cmd.append(OUTPUT_DIR + file.get_filename())
        subprocess.call(cmd)
        os.remove(OUTPUT_DIR + file.get_filename())
