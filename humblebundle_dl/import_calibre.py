import cPickle
import os
from os import listdir
from os.path import isfile, join
import subprocess

OUTPUT_DIR = "/Users/msei/Downloads/HB/"
OUTPUT_DIR = "/media/terra/MyBookEx/HB/"
CALIBRE_CMD = "/Applications/calibre.app/Contents/console.app/Contents/MacOS/calibredb"
CALIBRE_CMD = "/opt/calibre/calibredb"

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
        info = cPickle.load(handle)

    if info.humanName not in books:
        books[info.humanName] = list()

    books[info.humanName].append(info)


def touch_file(filename):
    with open(filename, 'w') as f:
        pass


def add_to_calibre(book_info):

    prime_book = 0
    for file in book_info:
        # we assume that the pdf version has the best metadata
        f = OUTPUT_DIR + "/" + file.get_filename()
        (ignored, ext) = os.path.splitext(f)
        if 'pdf' in ext:
            break
        prime_book += 1

    if prime_book > len(book_info) - 1:
        prime_book = 0

    cmd = list()
    cmd.append(CALIBRE_CMD)
    cmd.append("add")
    # cmd.append("--empty")
    cmd.append("--title")
    cmd.append(book_info[prime_book].humanName)
    already_imported = book_info[prime_book]
    cmd.append("--tags")
    cmd.append("HUMBLE_BUNDLE," + already_imported.get_bundle_name())
    cmd.append("--dont-notify-gui")
    cmd.append("--languages")
    cmd.append("en")
    f = OUTPUT_DIR + already_imported.get_filename()
    cmd.append(f)
    calibre_output = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE).stdout.read()
    touch_file(f + ".calibre_imported")
    book_id = -1
    try:
        book_id = int(calibre_output.split('\n')[1].replace("Added book ids: ", ""))
    except Exception, e:
        print calibre_output
        raise e
    for file in book_info:
        if file.get_filename() == already_imported.get_filename():
            continue
        cmd = list()
        cmd.append(CALIBRE_CMD)
        cmd.append("add_format")
        cmd.append("--dont-notify-gui")
        cmd.append("--dont-replace")
        cmd.append(str(book_id))
        f = OUTPUT_DIR + file.get_filename()
        cmd.append(f)
        subprocess.call(cmd)
        touch_file(f + ".calibre_imported")
        # os.remove(f)


for book_name in books:
    book_info = books[book_name]

    if len(book_info) == 0:
        continue

    # If one file is missing this either means there is an error (which can always happen in scripts ;) ) or we already
    # have imported one format. The code below would create duplicate entries in this case, so we skip this book
    can_import = 0
    for file in book_info:
        if not os.path.exists(OUTPUT_DIR + file.get_filename()):
            can_import += 1
        if os.path.exists(OUTPUT_DIR + file.get_filename() + ".calibre_imported"):
            can_import += 1

    if can_import > 0:
        print book_name, "Can't be imported " + str(can_import) + " files are missing from " + str(len(book_info))
        continue

    print book_name

    temp = dict()
    for file in book_info:  # file is DownloadLink
        f = OUTPUT_DIR + file.get_filename()
        (ignored, ext) = os.path.splitext(f)
        if ext in temp:
            if os.path.getsize(OUTPUT_DIR + temp[ext].get_filename()) < os.path.getsize(f):
                temp[ext] = file
        else:
            temp[ext] = file

    filtered_book_info = list()
    for ext in temp:
        filtered_book_info.append(temp[ext])
        # print "*", temp[ext].get_filename()


    try:
        add_to_calibre(filtered_book_info)
    except Exception, e:
        print "Error adding the book ", book_name, " maybe parsing the id failed or the subcommand?"
        print e
        print "---"
        continue
