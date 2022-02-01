import os
import re

TRAKTOR_RECORDING_NAME_PATTERN = r'\d{4}-\d{2}-\d{2}_\d{2}h\d{2}m\d{2}.\w+'
PARTITIONS = ["C:\\", "D:\\", "E:\\", "F:\\", "Y:\\", "Z:\\"]


def filter_by_pattern(string, pattern):
    filtered = []
    for name in string:
        if re.match(pattern, name):
            filtered.append(name)
    return filtered


def list_files_by_pattern(folders, name_pattern):
    files_by_pattern = []
    for folder_name in folders:
        for i in os.walk(folder_name):
            results = filter_by_pattern(i[2], name_pattern)
            for file_name in results:
                full_path = i[0] + os.sep + file_name
                files_by_pattern.append(full_path)
    return files_by_pattern


def save_m3u8(name, folder=None, file_path_names=None):
    with open(folder + os.sep + name + ".m3u8", "w") as file:
        for n in file_path_names:
            file.write(n + '\n')


if __name__ == '__main__':
    files = list_files_by_pattern(PARTITIONS, TRAKTOR_RECORDING_NAME_PATTERN)
    save_m3u8("traktor_recordings", "E:\\", files)
