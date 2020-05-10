import os
import subprocess
from optparse import OptionParser
import logging
import audible_dl_v2.utils as utils

FFMPEG = "/usr/local/bin/ffmpeg"


def create_logger():
    global logger
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def create_cmd_line_parser():
    parser = OptionParser(usage="Usage: %prog [options]", version="%prog 0.2")
    parser.add_option("--activation_bytes",
                      action="store",
                      dest="activation_bytes",
                      default="",
                      help="Audible activation bytes for decrypting")
    parser.add_option("--directory",
                      action="store",
                      dest="directory",
                      default="./dl/",
                      help="Source and output directory")
    parser.add_option("--impostors",
                      action="store_true",
                      dest="impostors",
                      default=False,
                      help="Overwrite the aax source file with a zero byte file. Reduces disc size.")
    return parser


def write_impostor(file):
    logger.info("Overwriting with impostor %s" % file)
    with open(file, 'w') as f:
        f.write("")


if __name__ == "__main__":
    create_logger()
    cmd_line_parser = create_cmd_line_parser()
    (options, args) = cmd_line_parser.parse_args()

    if options.activation_bytes is None:
        logger.error("--activation_bytes is missing")
        os.exit(-1)

    output_dir = os.path.abspath(options.directory)
    for file in utils.find_files(output_dir, "aax"):
        logger.info("Found %s" % file)
        file_wo_ext = file[:-3]

        # does the output file already exist?
        if os.path.exists(file_wo_ext + "aac"):
            if options.impostors:
                write_impostor(file)

            logger.info("Skipping file, output does already exist.")
            continue

        logger.info("Converting...")

        result = subprocess.run([
            FFMPEG,
            "-loglevel", "error",
            "-activation_bytes", options.activation_bytes,
            "-i", file,
            "-c:a", "copy",
            "-vn",
            "-f", "mp4",
            file_wo_ext + "aac"
        ], capture_output=True)
        logging.info(result.stderr)
        logging.info(result.stdout)

        logger.info("...done.")

        if options.impostors:
            write_impostor(file)
