import pathlib
import subprocess
import multiprocessing
import pickle
import jsonl

import time
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
    paths = [pathlib.Path(file['path']) for file in load_fingerprints(music_data_dir)]
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
    if len(nums_a) > len(nums_b):
        nums_a = nums_a[: len(nums_b)]
    elif len(nums_a) < len(nums_b):
        nums_b = nums_b[: len(nums_a)]

    covariance = 0
    for i in range(len(nums_a)):
        covariance += 32 - bin(nums_a[i] ^ nums_b[i]).count('1')
    covariance = covariance / float(len(nums_a))
    return covariance / 32


def cross_correlation(nums_a, nums_b, offset):
    if offset > 0:
        nums_a = nums_a[offset:]
        nums_b = nums_b[: len(nums_a)]
    elif offset < 0:
        offset = -offset
        nums_b = nums_b[offset:]
        nums_a = nums_a[: len(nums_b)]

    if min(len(nums_a), len(nums_b)) < min_overlap:
        raise Exception('Overlap too small: %i' % min(len(nums_a), len(nums_b)))

    # cross correlate nums_a and nums_b with offsets from -span to span
    return correlation(nums_a, nums_b)


def collect_all_cross_correlations(nums_a, nums_b, span, step):
    if span > min(len(nums_a), len(nums_b)):
        # Error checking in main program should prevent us from ever being
        # able to get here.
        raise Exception(
            'span >= sample size: %i >= %i\n'
            % (span, min(len(nums_a), len(nums_b)))
            + 'Reduce span, reduce crop or increase sample_time.'
        )

    correlations_of_pair = []
    for offset in numpy.arange(-span, span + 1, step):
        correlations_of_pair.append(cross_correlation(nums_a, nums_b, offset))

    return correlations_of_pair


def max_index(nums_a):
    max_index = 0
    max_value = nums_a[0]
    for i, value in enumerate(nums_a):
        if value > max_value:
            max_value = value
            max_index = i
    return max_index


def get_max_correlation(pair):
    correlations = collect_all_cross_correlations(
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


def calculate_correlations(files):
    print('================ Calculaing correlations started. ================')
    pairs_expected = (len(files) ** 2 - len(files)) // 2
    time_expected = pairs_expected / 27000 * 16.4375 / 3600
    print(f'Expected number of pairs: {pairs_expected:,}')
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


def collect_correlations(music_data_dir):
    files = load_fingerprints(music_data_dir)
    for file in files:
        file['path'] = str(file['path'])
    print('Total audio fingerprints:', len(files))
    corrs = calculate_correlations(files)

    corrs_path = music_data_dir.joinpath('correlations')
    jsonl.dump(corrs, corrs_path)
    print(f'Correlation data saved to "{corrs_path}".')


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
    corr = collect_all_cross_correlations(source_file['chp_fingerprint'],
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