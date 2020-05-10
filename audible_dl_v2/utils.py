import os


class Book:
    def __init__(self, title, author, dl_link, title_image, asin, series_asin):
        self.title = title
        self.author = author
        self.dl_link = dl_link
        self.title_image = title_image
        self.asin = asin
        self.series_asin = series_asin
        self.language = None


class SeriesElement:
    def __init__(self, asin, title, subtitle, authorLabel, narratorLabel, runtimeLabel):
        self.runtimeLabel = runtimeLabel
        self.narratorLabel = narratorLabel
        self.authorLabel = authorLabel
        self.subtitle = subtitle
        self.title = title
        self.asin = asin


class Chapter:
    def __init__(self, frame_start, frame_end, name, level):
        self.frame_start = frame_start
        self.frame_end = frame_end
        self.name = name
        self.type = level


def find_files(directory, extension):
    ret = list()

    for subdir, dirs, files in os.walk(directory):
        for file in files:
            if file[len(file) - 3:] != extension:
                continue

            f = os.path.join(subdir, file)
            ret.append(f)

    return ret
