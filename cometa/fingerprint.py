import pathlib
import subprocess
import multiprocessing
import pickle
import json

import time
import random

import numpy
import tqdm

import config


test = False

"""
if test:
    music_dirs = [
        pathlib.Path(r'F:\mocking_data\music\music_in'),
    ]
    dump_path = pathlib.Path(r'F:\mocking_data\music\fingerprints.pickle')
    corrs_path = pathlib.Path(r'F:\mocking_data\music\correlations.json')
else:
    music_dirs = [
        pathlib.Path(r'F:\Natalia\Google Диск\Music_Roaming'),
        pathlib.Path(r'F:\Natalia\Music'),
    ]
    dump_path = pathlib.Path(r'F:\Natalia\Music Data\fingerprints.pickle')
    corrs_path = pathlib.Path(r'F:\Natalia\Music Data\correlations.json')
"""

# seconds to sample audio file for
sample_time = 500  # number of points to scan cross correlation over
span = 0  # 150  # step size (in points) of cross correlation
step = 1  # minimum number of points that must overlap in cross correlation

# exception is raised if this cannot be met
min_overlap = 20  # report match when cross correlation has a peak
# exceeding threshold
threshold = 0.6


def calculate_fingerprint(file):
    try:
        fpcalc_out = subprocess.getoutput(
            'fpcalc -raw -length %i "%s"'
            % (
                sample_time,
                file['path'],
            )
        )
        duration_start_index = fpcalc_out.find('DURATION=') + 9
        duration_end_index = fpcalc_out.find('\n')
        duration = int(fpcalc_out[duration_start_index:duration_end_index])

        fingerprint_index = fpcalc_out.find('FINGERPRINT=') + 12
        fingerprint = list(map(int, fpcalc_out[fingerprint_index:].split(',')))
    except ValueError:
        duration = 0
        fingerprint = []
    file['chp_duration'] = duration
    file['chp_fingerprint'] = fingerprint
    return file


def correlation(listx, listy):
    if not listx or not listy:
        raise Exception('Empty lists cannot be correlated.')

    if len(listx) > len(listy):
        listx = listx[: len(listy)]
    elif len(listx) < len(listy):
        listy = listy[: len(listx)]

    covariance = 0
    for i in range(len(listx)):
        covariance += 32 - bin(listx[i] ^ listy[i]).count('1')
    covariance = covariance / float(len(listx))
    return covariance / 32


def cross_correlation(listx, listy, offset):
    if offset > 0:
        listx = listx[offset:]
        listy = listy[: len(listx)]
    elif offset < 0:
        offset = -offset
        listy = listy[offset:]
        listx = listx[: len(listy)]

    # if min(len(listx), len(listy)) < min_overlap:
    #    raise Exception('Overlap too small: %i' % min(len(listx), len(listy)))

    # cross correlate listx and listy with offsets from -span to span
    return correlation(listx, listy)


def compare(listx, listy, span, step):
    if span > min(len(listx), len(listy)):
        # Error checking in main program should prevent us from ever being
        # able to get here.
        raise Exception(
            'span >= sample size: %i >= %i\n'
            % (span, min(len(listx), len(listy)))
            + 'Reduce span, reduce crop or increase sample_time.'
        )

    corr_xy = []
    for offset in numpy.arange(-span, span + 1, step):
        corr_xy.append(cross_correlation(listx, listy, offset))

    return corr_xy


def max_index(listx):
    max_index = 0
    max_value = listx[0]
    for i, value in enumerate(listx):
        if value > max_value:
            max_value = value
            max_index = i
    return max_index


def print_max_corr(corr, source_path, target_path):
    max_corr_index = max_index(corr)
    max_corr_offset = -span + max_corr_index * step

    print(
        'max_corr_index = ',
        max_corr_index,
        'max_corr_offset = ',
        max_corr_offset,
    )

    if corr[max_corr_index] > threshold:
        print(
            (
                '%s and %s match with correlation of %.4f at offset %i'
                % (
                    source_path,
                    target_path,
                    corr[max_corr_index],
                    max_corr_offset,
                )
            )
        )
    else:
        print('No statistically significant correlation was found.')


def print_correlation(source_path, target_path):
    fingerprint_source = calculate_fingerprints(source_path)
    fingerprint_target = calculate_fingerprints(target_path)
    corr = compare(fingerprint_source, fingerprint_target, span, step)

    print(
        f'duration_source = {duration_source},',
        f'duration_target = {duration_target}',
    )
    print(
        f'len_source = {len(fingerprint_source)},',
        f'len_target = {len(fingerprint_target)}',
    )
    ratio_source = len(fingerprint_source) / duration_source
    ratio_target = len(fingerprint_target) / duration_target
    print(f'ratio_source = {ratio_source}, ratio_target = {ratio_target}')

    print_max_corr(corr, source_path, target_path)


def get_max_correlation(pair):
    correlations = compare(
        pair[0]['chp_fingerprint'], pair[1]['chp_fingerprint'], span, step,
    )
    max_corr_index = max_index(correlations)

    max_corr_value = correlations[max_corr_index]
    max_corr_offset = -span + max_corr_index * step
    pair = [
        pair[0]['path'],
        pair[1]['path'],
        max_corr_value,
        max_corr_offset,
    ]
    return pair


def count_extentions(paths):
    exts = {}
    for p in paths:
        ext = p.suffix
        if ext in exts.keys():
            exts[ext] += 1
        else:
            exts[ext] = 1
    return exts


def get_paths(basic_paths):
    paths = []
    for dir in basic_paths:
        for p in dir.rglob('*'):
            if p.is_file():
                paths.append(p)
    return paths


def get_fingerprints(files):
    # with multiprocessing.Pool() as pool:
    #     results = pool.map(calculate_fingerprint, files)
    pool = multiprocessing.Pool()
    results = []
    for result in tqdm.tqdm(
        pool.imap_unordered(calculate_fingerprint, files), total=len(files)
    ):
        results.append(result)
    # pool.close()
    # pool.join()
    # process_bar.close()
    return [file for file in results if file['chp_fingerprint']]


def dump_file_data(path, files):
    with open(path, 'wb') as datafile:
        pickle.dump(files, datafile)


def load_file_data(path):
    with open(path, 'rb') as datafile:
        files = pickle.load(datafile)
    return files


def dump_music_dir_fingerprints(dirs_to_scan, path_to_dump):
    print('Collecting file paths...')
    files = [{'path': p} for p in get_paths(dirs_to_scan)]
    print(f'Done. Files found: {len(files)}.')

    print('Creating audio fingerprints...')
    files = get_fingerprints(files)
    print('Done.')

    dump_file_data(path_to_dump, files)
    print(f'Audio fingerprints saved to "{path_to_dump}".')
    print('No new tasks. Process terminated.')


def get_correlations(files):
    print('================ Calculaing correlations started. ================')
    pairs_expected = (len(files) ** 2 - len(files)) // 2
    time_expected = pairs_expected / 27000 * 16.4375 / 3600
    print('Expected number of pairs:', pairs_expected)
    print(f'Expected time: {time_expected:.03f} hours')

    pairs = []
    for index, file_a in enumerate(files, 1):
        pairs_chunk = []
        for file_b in files[index:]:
            pairs_chunk.append([file_a, file_b])

        print(f'Iteration: {index:5}  |  ', end='')
        start = time.time()

        with multiprocessing.Pool() as pool:
            results_chunk = pool.map(get_max_correlation, pairs_chunk)

        elapsed = time.time() - start
        print(f'Elapsed: {elapsed:8.3f} s  |  ', end='')
        performance = len(results_chunk) / elapsed
        print(f'Performance: {performance:5.0f} correlations/s')

        pairs.extend(results_chunk)
    print('=============== Calculaing correlations finished. ================')
    return pairs


def handle_1(dump_path, corrs_dump_path):
    files = load_file_data(dump_path)
    for file in files:
        file['path'] = str(file['path'])
    # files = [file for file in load_file_data(dump_path) if file['chp_fingerprint']]
    print('Total audio fingerprints:', len(files))
    # files[:] = random.sample(files, 5)
    corrs = get_correlations(files)
    # corrs = [file[2] for file in corrs]
    # corrs.sort(reverse=True)
    with open(corrs_dump_path, 'w') as file:
        json.dump(corrs, file)
        print(f'Correlation data saved to {corrs_dump_path}.')
    # for i in range(25, 31):
    #    print(len(get_correlations(short[:1000*i])))


def overview_audio_files(dump_path):
    paths = [file['path'] for file in load_file_data(dump_path)]
    print('Audio detected in files with extentions:')
    print(count_extentions(paths))

    music_exts = ['.mp3', '.flac', '.m4a', '.ogg', '.mka', '.wma']
    unexpected_files = [
        path for path in paths if path.suffix not in music_exts
    ]
    if unexpected_files:
        print('Files with unexpected audio:')
        [print(path) for path in unexpected_files]


if __name__ == '__main__':
    dump_music_dir_fingerprints(music_dirs, dump_path)
    # overview_audio_files(dump_path)
    # handle_1(dump_path, corrs_path)
