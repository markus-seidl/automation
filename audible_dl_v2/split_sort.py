import shutil
import subprocess
import os
import io
import sys
import jsons
import json
from optparse import OptionParser
import logging
import utils as utils
# pip3 install --upgrade pyyaml
import yaml
from pathlib import Path
import string
import unicodedata
import traceback
import multiprocessing

# For multithreading on MACOS make sure to add OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES into env

# brew install taglib (on macos!)
# libtag1-dev for debian / ubuntu and derivates
import taglib

import re

# pip install --upgrade google-cloud-speech


import tempfile

# brew install ffmpeg
FFMPEG = "/usr/local/bin/ffmpeg"
# brew install atomicparsley
ATOMICPARSLEY = "/usr/local/bin/atomicparsley"

if sys.platform == 'linux':
    FFMPEG = "/usr/bin/ffmpeg"
    ATOMICPARSLEY = "/usr/bin/AtomicParsley"

VALID_FILENAME_CHARS = "-_.() %s%s" % (string.ascii_letters, string.digits)


def remove_disallowed_filename_chars(filename):
    cleaned_filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
    return ''.join(chr(c) for c in cleaned_filename if chr(c) in VALID_FILENAME_CHARS)


def transcribe_file(input_file, frame_start, frame_end, language, chapter_idx):
    """Transcribe the given audio file."""
    global google_speech_client

    from google.cloud import speech
    from google.cloud.speech import enums
    from google.cloud.speech import types

    try:
        google_speech_client
    except NameError:
        google_speech_client = speech.SpeechClient()
        logger.info("Creating google speech client")

    frame_length = 15 * 1000
    if chapter_idx == 0:
        frame_length *= 2  # first chapter contains "Willkommen bei Audible..." which takes around 15 seconds :(

    # encode audio and load it
    frame_end_new = min(frame_end, frame_start + frame_length)  # only transcribe 15 seconds

    with tempfile.NamedTemporaryFile(suffix='.opus') as speech_file:
        split_to_opus(input_file, speech_file.name, frame_start, frame_end_new)

        with io.open(speech_file.name, 'rb') as audio_file:
            content = audio_file.read()

    language_code = 'de-DE'
    if str(language).lower() == 'englisch':
        language_code = 'en-GB'

    audio = types.RecognitionAudio(content=content)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.OGG_OPUS,
        use_enhanced=True,
        sample_rate_hertz=24000,
        language_code=language_code,
        # alternativeLanguageCodes=['en-US']
        # model=,

    )

    logger.info("Requesting transcription from google in <%s> for <%s> (%i-%i)..." % (
        language_code, input_file, frame_start, frame_end
    ))
    try:
        response = google_speech_client.recognize(config, audio)
    except:
        logger.error("Error while calling google:")
        logger.error(sys.exc_info()[0])
        print(traceback.print_exc())
        return None

    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.

    # for result in response.results:
    # The first alternative is the most likely one for this portion.
    #     print(u'Transcript: {}'.format(result.alternatives[0].transcript))

    if len(response.results) == 0 or len(response.results[0].alternatives) == 0:
        print(response)
        return ""

    ret = response.results[0].alternatives[0].transcript
    logger.info("- Got transcript <%s>" % ret)

    return ret


def create_logger():
    global logger

    try:
        logger
    except NameError:
        logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)


def create_cmd_line_parser():
    parser = OptionParser(usage="Usage: %prog [options]", version="%prog 0.1")
    parser.add_option("--input",
                      action="store",
                      dest="input_directory",
                      default="./dl/",
                      help="")
    parser.add_option("--output",
                      action="store",
                      dest="output_directory",
                      default=False,
                      help="")
    return parser


def add_album_art(audio_file, art_file):
    cmd = [
        ATOMICPARSLEY,
        audio_file,
        '--artwork',
        art_file,
        '--overWrite'
    ]

    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def add_album_art_old(audio_file, art_file):
    try:
        cmd = [
            ATOMICPARSLEY,
            audio_file,
            '--artwork',
            art_file,
            '--overWrite'
        ]

        process = subprocess.Popen(
            cmd,
            # stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL  # sys.stderr
        )
    except OSError as e:
        print(traceback.print_exc())
        raise e

    out = process.communicate()
    process.terminate()
    if process.returncode != 0:
        raise IOError(out[0], out[1])

    return out


def ffmpeg(cmd):
    cmd.insert(0, FFMPEG)
    cmd.insert(1, '-loglevel')
    cmd.insert(2, 'warning')

    subprocess.check_call(cmd)


def ffmpeg_old(cmd):
    try:
        cmd.insert(0, FFMPEG)
        cmd.insert(1, '-loglevel')
        cmd.insert(2, 'warning')

        process = subprocess.Popen(
            cmd,
            # stdin=subprocess.PIPE,
            # stdout=subprocess.DEVNULL,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
    except OSError as e:
        print(traceback.print_exc())
        raise e

    out = process.communicate()
    process.terminate()
    if process.returncode != 0:
        raise IOError(out[0], out[1])

    return out


def split(input_file, output_file, from_frame, to_frame):
    from_second = from_frame / 1000.0
    to_second = to_frame / 1000.0

    return ffmpeg([
        '-i',
        input_file,
        '-map_metadata',
        '-1',
        '-acodec',
        'copy',
        '-ss',
        str(from_second),
        '-to',
        str(to_second),
        output_file
    ])


def split_to_flac(input_file, output_file, from_frame, to_frame):
    from_second = from_frame / 1000.0
    to_second = to_frame / 1000.0

    return ffmpeg([
        '-i',
        input_file,
        '-map_channel',
        '0.0.0',
        '-c:a',
        'flac',
        # '-sample_fmt',
        # 's16',
        '-af',
        'aformat=s16:22050',
        '-ss',
        str(from_second),
        '-to',
        str(to_second),
        output_file,
        '-y'
    ])


def split_to_opus(input_file, output_file, from_frame, to_frame):
    from_second = from_frame / 1000.0
    to_second = to_frame / 1000.0

    return ffmpeg([
        '-i',
        input_file,
        '-map_channel',
        '0.0.0',
        '-c:a',
        'libopus',
        '-b:a',
        '96K',
        # '-sample_fmt',
        # 's16',
        '-af',
        'aformat=s16:24000',
        '-ss',
        str(from_second),
        '-to',
        str(to_second),
        output_file,
        '-y'
    ])


def read_book(file):
    with open(file) as f:
        # b = jsons.load(f.read(), utils.Book)
        b = json.load(f)
        temp = utils.Book(b['title'], b['author'], None, None, b['asin'], b['series_asin'])
        temp.language = b['language']
        return temp


def read_series(file):
    ret = list()
    with open(file) as f:
        # b = jsons.load(f.read(), utils.SeriesElement)
        b = json.load(f)

        for e in b:
            ret.append(utils.SeriesElement(e['asin'], e['title'], e['subtitle'], e['authorLabel'], None, None))

    return ret


def find_series_idx(series_info, book_asin):
    i = 0
    for series in series_info:
        if series.asin == book_asin:
            return i

        i += 1

    return -1


def read_chapters(file):
    ret = list()
    with open(file) as f:
        j = json.load(f)

    if j is None:
        return ret

    chapters = j['cloudPlayerChapters']
    for chapter in chapters:
        ret.append(utils.Chapter(
            int(chapter['chapterStartPosition']),
            int(chapter['chapterEndPosition']),
            chapter['chapterTitle'],
            chapter['level']
        ))

    return ret


class OutputInformation:
    def __init__(self, artist_dir, album_dir, artist, album, sort_album, language, series_idx, skip, book_info_filename,
                 book_info):
        self.artist_dir = artist_dir
        self.album_dir = album_dir
        self.artist = artist
        self.album = album
        self.sort_album = sort_album
        self.language = language
        self.series_idx = series_idx
        self.skip = skip
        self.book_info_filename = book_info_filename
        self.book_info = book_info


def find_transcription(transcriptions, input_file, frame_start, frame_end, language, chapter_idx):
    if str(frame_start) in transcriptions:
        out = sanitize_transcription(transcriptions[str(frame_start)])
        if out is not None:
            return out

    trans = transcribe_file(input_file, frame_start, frame_end, language, chapter_idx)
    if trans is None:
        return trans

    transcriptions[frame_start] = trans

    return sanitize_transcription(trans)


def sanitize_transcription(trans):
    if trans is None:
        return None, None

    trans = str(trans).title()
    len_before = len(trans)

    audible1 = re.compile(re.escape('willkommen bei audible'), re.IGNORECASE)
    audible2 = re.compile(re.escape('gute unterhaltung'), re.IGNORECASE)
    audible3 = re.compile(re.escape('this is audible'), re.IGNORECASE)

    trans = audible1.sub('', trans)
    trans = audible2.sub('', trans)
    trans = audible3.sub('', trans)

    if len_before > 0 and len(trans.strip()) == 0:
        # Audio clip only contained "Willkommen bei Audible..." :(
        return "Audible Vorspann", "Audible Vorspann"

    ret_short = ""
    for word in str(trans).split(' '):
        if word.isspace():
            continue

        ret_short += word + " "
        if len(ret_short) > 30:
            break

    ret_long = ""
    for word in str(trans).split(' '):
        if word.isspace():
            continue

        ret_long += word + " "
        if len(ret_long) > 60:
            break

    return ret_short.strip(), ret_long.strip()


def split_src_into_chapters(input_file, output_dir, tags, chapter_info):
    title_output_dir = output_dir + "/" + make_filename_sane(tags.artist_dir) \
                       + "/" + make_filename_sane(tags.album_dir) + "/"

    Path(title_output_dir).mkdir(parents=True, exist_ok=True)

    info_file = title_output_dir + "/" + tags.book_info.asin
    if not os.path.exists(info_file):
        shutil.copy(tags.book_info_filename, info_file)

    transcriptions = dict()
    transcriptions_file = input_file[:-3] + "transcriptions"
    if os.path.exists(transcriptions_file):
        with open(transcriptions_file) as f:
            transcriptions = json.load(f)

    # if str(tags.language).lower() == 'englisch':
    #     transcriptions = dict()

    len_trans_before = len(transcriptions)

    i = 1
    for chapter in chapter_info:
        try:
            title_file = chapter.name
            title_tag = chapter.name

            if "kapitel" in title_file.lower() or "chapter" in title_file.lower():
                temp = find_transcription(transcriptions, input_file, chapter.frame_start, chapter.frame_end,
                                          tags.language, i)
                if temp is not None and temp[0] is not None and temp[1] is not None and len(str(temp[0])) > 5:
                    title_file = temp[0]
                    title_tag = temp[1]

            chapter_file = title_output_dir + "%03i " % i + make_filename_sane(title_file) + ".m4a"

            if os.path.exists(chapter_file):
                # logger.info("- Skipping chapter writing chapter file <%s>." % chapter_file)
                i += 1
                continue

            logger.info("Processing chapter %s for %s" % (input_file, chapter.name))

            dry_run = False
            if not dry_run:
                split(input_file, chapter_file, chapter.frame_start, chapter.frame_end)

                chapter_tags = taglib.File(chapter_file)
                chapter_tags.tags['ARTIST'] = tags.artist
                chapter_tags.tags['ALBUM'] = tags.album
                chapter_tags.tags['ALBUMSORT'] = tags.sort_album
                chapter_tags.tags['TITLE'] = title_tag
                # ARTISTSORT
                # DISCNUMBER
                # TITLESORT
                chapter_tags.tags['TRACKNUMBER'] = "%i/%i" % (i, len(chapter_info))
                chapter_tags.save()
                chapter_tags.close()

                add_album_art(chapter_file, input_file[:-3] + 'jpg')

            # save translations on every loop, for better restart behaviour
            if not os.path.exists(transcriptions_file) or len_trans_before != len(transcriptions):
                with open(transcriptions_file, 'w+') as f:
                    f.write(jsons.dumps(transcriptions))

            i += 1
        except IOError as e:
            logger.error(e)
            logger.error("Skipping this chapter %i. Please rerun." % i)
            i += 1
            # print(traceback.print_exc())


def process_adjustments(book_info, series_info, adjustment_list, key, haystack):
    relevant_adjustments = list()
    for cat in adjustment_list:
        if key in cat:
            relevant_adjustments.append(cat[key])

    for adj_list in relevant_adjustments:
        for adj in adj_list:
            find = adj['find']
            replace = adj['replace']
            haystack = re.sub(find, replace, haystack)

    return haystack


def generate_output_information(input_dir, book_info, overrides, book_info_filename):
    series_info = None

    if book_info.series_asin is not None:
        series_info = read_series(input_dir + "/" + book_info.series_asin + ".series_info")

    title = book_info.title
    author = book_info.author
    display_title = book_info.title
    skip = False

    series_idx = -1
    if series_info:
        # Add title number to the album name / title
        series_idx = find_series_idx(series_info, book_info.asin) + 1

        if book_info.series_asin in overrides:
            series_overrides = overrides[book_info.series_asin]
            if 'index_regex' in series_overrides:
                idx_match = re.search(series_overrides['index_regex'], title)
                if idx_match:
                    series_idx = int(idx_match.group(1))
            if 'series_offset' in series_overrides:
                series_idx += int(series_overrides['series_offset'])

        title = "%03i" % series_idx + " " + title

    if book_info.series_asin in overrides:
        series_overrides = overrides[book_info.series_asin]
        if "author" in series_overrides:
            author = series_overrides['author']

        if "adjustments" in series_overrides:
            adjustments = series_overrides['adjustments']

            display_title = process_adjustments(book_info, series_info, adjustments, 'title', book_info.title)
            title = process_adjustments(book_info, series_info, adjustments, 'title', title)

    if book_info.asin in overrides:
        book_overrides = overrides[book_info.asin]
        if "author" in book_overrides:
            author = book_overrides['author']
        if "title" in book_overrides:
            title = str(book_overrides['title']).format(series_idx, title)
        if "skip" in book_overrides:
            skip = bool(book_overrides['skip'])
        if "series_idx" in book_overrides:
            series_idx = int(book_overrides['series_idx'])

    return OutputInformation(author, title, author, display_title, title, book_info.language, series_idx,
                             skip, book_info_filename, book_info), series_info


def override_chapters(book_info, original_chapters, overrides):
    if book_info.asin not in overrides:
        return original_chapters

    book_overrides = overrides[book_info.asin]

    if 'chapters' not in book_overrides:
        return original_chapters

    new_chapters = book_overrides['chapters']

    ret = list()
    for chapter in new_chapters:
        ret.append(utils.Chapter(
            int(chapter['begin']),
            int(chapter['end']),
            chapter['name'],
            chapter['level'] if 'level' in chapter else 'CHAPTER'
        ))

    return ret


def make_filename_sane(name):
    if name is None:
        return None

    name = name.replace(':', '_').replace('/', '_').replace('?', '_').replace('.', '')
    name = name.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')

    return remove_disallowed_filename_chars(name).strip(' ')


def process(file, overrides, input_dir, output_dir, options):
    # logger.info("Found %s" % file)
    file_wo_ext = file[:-3]
    book_info_filename = file_wo_ext + "bookinfo"
    book_info = read_book(book_info_filename)
    chapter_info = read_chapters(file_wo_ext + "chapters")
    tags, series_info = generate_output_information(input_dir, book_info, overrides, book_info_filename)

    if tags.skip:
        logger.info("Skipping because requested: %s" % file)
        return

    split_src_into_chapters(file_wo_ext + "m4b", output_dir, tags,
                            override_chapters(book_info, chapter_info, overrides))
    if tags.series_idx == 1 and not os.path.exists(file_wo_ext + "jpg"):
        # first title use cover image as poster for the whole author
        title_output_dir = output_dir + "/" + make_filename_sane(tags.artist_dir) + "/poster.jpg"
        shutil.copy(file_wo_ext + "jpg", title_output_dir)


def process_unwrap(obj):
    if obj is None:
        return

    create_logger()

    process(obj[0], obj[1], obj[2], obj[3], obj[4])


if __name__ == '__main__':
    create_logger()
    cmd_line_parser = create_cmd_line_parser()
    (options, args) = cmd_line_parser.parse_args()

    output_dir = os.path.abspath(options.output_directory)
    input_dir = os.path.abspath(options.input_directory)

    with open('split_sort_overrides.yaml', 'r') as stream:
        overrides = yaml.load(stream, Loader=yaml.FullLoader)

    single_task = False

    files = utils.find_files(input_dir, "m4b")

    if single_task:
        for file in files:
            process(file, overrides, input_dir, output_dir, options)
    else:
        # convert file into an object that can be put into process
        data = list()
        for file in files:
            data.append([file, overrides, input_dir, output_dir, options])

        with multiprocessing.get_context("spawn").Pool(3) as p:
            p.map(process_unwrap, data)
