import pathlib
import psutil
import subprocess
import multiprocessing
#import pickle
import jsonl

import time
import datetime
import random

import numpy
import tqdm


# seconds to sample audio file for
sample_time = 500

# number of points to scan cross correlation over
span = 0  # 150

# step size (in points) of cross correlation
step = 1

# minimum number of points that must overlap in cross correlation
# exception is raised if this cannot be met
min_overlap = 0  # 20

# If cross-correlation peaked below this threshold
# then files are not considered a match.
# If above then files may be (but need not be) a duplicate.
threshold = 0.6

# Bytes per correlation pair. When decreased, size of dumps will increase, so
# Pandas will lack of memory to load it. If decrease - correlation performance
# will decreased, and will be more dump files.

bytes_per_correlation_pair = 1150  # * 10**4

# This sets the maximum number of records that developer can comfortably
# load to memory (3.5 Gb free) with Pandas at a time.
# On load Pandas take 1150 bytes of memory per record.
dump_size_limit = 3_000_000


def str_no_microseconds(elapsed):
    return str(elapsed).split('.')[0]


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


def get_fingerprints(files):
    pool = multiprocessing.Pool()
    results = []
    for result in tqdm.tqdm(
        pool.imap_unordered(calculate_fingerprint, files), total=len(files)
    ):
        results.append(result)
    return [file for file in results if file['chp_fingerprint']]


def get_paths(basic_paths):
    paths = []
    for dir in basic_paths:
        for p in dir.rglob('*'):
            if p.is_file():
                paths.append(p)
    return paths


def dump_fingerprints(music_data_dir, files):
    dump_path = music_data_dir.joinpath('fingerprints')
    jsonl.dump(files, dump_path)
    #with dump_path.with_suffix('.pickle').open('wb') as dump_file:
    #    pickle.dump(files, dump_file)
    print(f'Audio fingerprints saved to "{dump_path}".')


def load_fingerprints(music_data_dir):
    dump_path = music_data_dir.joinpath('fingerprints')
    files = jsonl.load(dump_path)
    #with dump_path.with_suffix('.pickle').open('rb') as dump_file:
    #    files = pickle.load(dump_file)
    print(f'Audio fingerprints loaded from "{dump_path}".')
    return files


def collect_fingerprints(dirs_to_scan, path_to_dump):
    print('Collecting file paths...')
    files = [{'path': str(p)} for p in get_paths(dirs_to_scan)]

    print(f'Done. Files found: {len(files)}.')

    print('Creating audio fingerprints...')
    files = get_fingerprints(files)
    print('Done.')

    dump_fingerprints(path_to_dump, files)


def count_extentions(paths):
    exts = {}
    for p in paths:
        ext = p.suffix
        if ext in exts.keys():
            exts[ext] += 1
        else:
            exts[ext] = 1
    return exts


def overview_audio_files(music_data_dir):
    paths = ([pathlib.Path(file['path'])
              for file in load_fingerprints(music_data_dir)])
    print('Audio detected in files with extentions:')
    print(count_extentions(paths))

    music_exts = ['.mp3', '.flac', '.m4a', '.ogg', '.mka', '.wma']
    unexpected_files = [
        path for path in paths if path.suffix not in music_exts
    ]
    if unexpected_files:
        print('Files with unexpected audio:')
        [print(path) for path in unexpected_files]


def correlation(nums_a, nums_b):
    """Return correlation between lists of numbers"""

    if not nums_a or not nums_b:
        # Error checking in main program should prevent us from ever being
        # able to get here.
        raise Exception('Empty lists cannot be correlated.')

    # Shortening a longer sequence
    len_a = len(nums_a)
    len_b = len(nums_b)
    if len_a > len_b:
        nums_a = nums_a[: len_b]
    elif len_a < len_b:
        nums_b = nums_b[: len_a]

    # Chromaprint use fixed bit lenght
    bit_depth = 32
    bits_total = len(nums_a) * bit_depth
    bits_different = sum(
        [(a ^ b).bit_count() for a, b in zip(nums_a, nums_b)]
    )
    return 1 - bits_different / bits_total


def correlation_with_offset(nums_a, nums_b, offset):
    if offset > 0:
        nums_a = nums_a[offset:]
        nums_b = nums_b[: len(nums_a)]
    elif offset < 0:
        offset = -offset
        nums_b = nums_b[offset:]
        nums_a = nums_a[: len(nums_b)]

    if min(len(nums_a), len(nums_b)) < min_overlap:
        raise Exception('Overlap too small: %i' % min(len(nums_a),
                                                      len(nums_b)))

    # cross correlate nums_a and nums_b with offsets from -span to span
    return correlation(nums_a, nums_b)


def cross_correlation(nums_a, nums_b, span, step):
    if span > min(len(nums_a), len(nums_b)):
        # Error checking in main program should prevent us from ever being
        # able to get here.
        raise Exception(
            'span >= sample size: %i >= %i\n'
            % (span, min(len(nums_a), len(nums_b)))
            + 'Reduce span, reduce crop or increase sample_time.'
        )

    correlations_of_pair = []
    for offset in range(-span, span+1, step):
        correlations_of_pair.append(
            correlation_with_offset(nums_a, nums_b, offset)
        )
    return correlations_of_pair


def max_index(nums):
    max_ = max(nums)
    return max_, nums.index(max_)


def get_max_correlation(pair):
    correlations = cross_correlation(
        pair[0]['chp_fingerprint'], pair[1]['chp_fingerprint'], span, step,
    )
    max_corr_value, max_corr_index = max_index(correlations)
    max_corr_offset = -span + max_corr_index * step
    pair = [
        pair[0]['path'],
        pair[1]['path'],
        max_corr_value,
        max_corr_offset,
    ]
    return pair


# TODO: generator??
def calculate_correlations(files, music_data_dir):
    func_start = datetime.datetime.now()
    print(f'Calculaing correlations started at',
          str_no_microseconds(func_start))
    pairs_expected = (len(files) ** 2 - len(files)) // 2
    pairs_saved = 0
    print(f'Expected number of pairs: {pairs_expected:,}')
    print(' Iter |    Chunk Size      |   Performance  |'
          '  Elapsed |   End in  | Progress')
    iteration = 1
    while files:
        pairs_chunk = []
        free_memory = psutil.virtual_memory()[1]
        places_left = min(free_memory // bytes_per_correlation_pair,
                          dump_size_limit)
        # - len(files) + 1
        while places_left > 0 and files:
            chosen_file = files.pop()
            pairs_chunk.extend([[chosen_file, file] for file in files])
            places_left -= len(files)

        print(f'{iteration:5} |', end='')
        share = len(pairs_chunk) / pairs_expected
        print(f' {len(pairs_chunk):8} ({share:7.2%}) |', end='')
        iter_start = datetime.datetime.now()

        with multiprocessing.Pool() as pool:
            results_chunk = pool.map(get_max_correlation, pairs_chunk)

        elapsed = datetime.datetime.now() - iter_start
        performance = len(results_chunk) / elapsed.seconds
        print(f' {performance:7.0f} corr/s |', end='')
        print(f' {str_no_microseconds(elapsed):>8} |  ', end='')

        corrs_path = music_data_dir.joinpath(f'correlations_{iteration:03}')
        jsonl.dump(results_chunk, corrs_path)  # generator yield here
        #  -> to external saving or sending or analysing or other handling
        # async call or thread for dumping/sending, but not for calculations
        end_in_seconds = (pairs_expected - pairs_saved) / performance
        end_in = datetime.timedelta(seconds=end_in_seconds)
        print(f' {str_no_microseconds(end_in)} |', end='')
        pairs_saved += len(results_chunk)
        print(f' {pairs_saved / pairs_expected:4.0%}')
        iteration += 1
    func_elapsed = datetime.datetime.now() - func_start
    print('Calculaing correlations finished in',
          str_no_microseconds(func_elapsed))


def collect_correlations(music_data_dir):
    files = load_fingerprints(music_data_dir)
    for file in files:
        file['path'] = str(file['path'])
    print('Total audio fingerprints:', len(files))

    calculate_correlations(files, music_data_dir)
    print(f'Correlation data saved to "{music_data_dir}".')


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
    
    source_file = calculate_fingerprint({'path': source_path})
    target_file = calculate_fingerprint({'path': target_path})
    corr = cross_correlation(source_file['chp_fingerprint'],
                                          target_file['chp_fingerprint'],
                                          span,
                                          step)
    print(
        f"duration_source = {source_file['chp_duration']},",
        f"duration_target = {target_file['chp_duration']}",
    )
    print(
        f"len_source = {len(source_file['chp_fingerprint'])},",
        f"len_target = {len(target_file['chp_fingerprint'])}",
    )
    ratio_source = (len(source_file['chp_fingerprint'])
                    / source_file['chp_duration'])
    ratio_target = (len(target_file['chp_fingerprint'])
                    / target_file['chp_duration'])
    print(f'ratio_source = {ratio_source}, ratio_target = {ratio_target}')

    print_max_corr(corr, source_path, target_path)