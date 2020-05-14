import glob


def all_metainf_files(download_dir):
    return glob.glob(download_dir + "/**/*.metainf", recursive=True)


def clean_type(type_str):
    type_str = str(type_str).strip(' ')
    if type_str == ".cbz":
        return "CBZ"
    return type_str.upper()