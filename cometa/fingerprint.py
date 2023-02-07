import pathlib
import psutil
import subprocess
import multiprocessing
import random

import time
import datetime
import tqdm

import jsonl


# seconds to sample audio file for fingerprint
SAMPLE_TIME = 5400

# number of fingerprint samples to scan cross correlation over
SPAN = 150

# step size (in fingerprint samples) of cross correlation
STEP = 1

# minimum number of fingerprint samples that must overlap in cross correlation
# exception is raised if this cannot be met
MIN_OVERLAP = 20

# threshold above which tracks are considered similar
# 1% of best matches has correlation greater than 0.577 on 83k files
THRESHOLD = 0.58

# The size (in bytes) reserved in memory for pair correlation calculations.
# If you reduce it, then performance will slightly increase,
# but the size of the dumps will also increase, and therefore
# there may not be enough memory to load the saved results later.
BYTES_PER_CORRELATION_PAIR = 1150

# Maximum number of entries in one dump file.
# The developer of this application has 3.5 GB of free memory on his laptop.
# When loaded into Pandas, each entry requires 1150 bytes of memory per entry,
# and 3 million entries requires 3.15 GB.
DUMP_SIZE_LIMIT = 3_000_000


def str_no_microseconds(elapsed):
    return str(elapsed).split('.')[0]


def calculate_fingerprint(file):
    try:
        fpcalc_out = subprocess.getoutput(
            'fpcalc -raw -length %i "%s"'
            % (
                SAMPLE_TIME,
                file['path'],
            )
        )

        fingerprint_index = fpcalc_out.find('FINGERPRINT=') + 12
        fingerprint = list(map(int, fpcalc_out[fingerprint_index:].split(',')))
    except ValueError:
        fingerprint = []
    file['fingerprint'] = fingerprint
    return file


def get_fingerprints(files, profiling=False):
    if profiling:
        tasks = map(calculate_fingerprint, files)
        results = [result for result in tqdm.tqdm(tasks, total=len(files))]
    else:
        pool = multiprocessing.Pool()
        tasks = pool.imap_unordered(calculate_fingerprint, files)
        results = [result for result in tqdm.tqdm(tasks, total=len(files))]
    return [file for file in results if file['fingerprint']]


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
    print(f'Audio fingerprints saved to "{dump_path}".')


def load_fingerprints(music_data_dir):
    dump_path = music_data_dir.joinpath('fingerprints')
    files = jsonl.load(dump_path)
    print(f'Audio fingerprints loaded from "{dump_path}".')
    return files


def collect_fingerprints(dirs_to_scan, path_to_dump, profiling=False):
    fp_start = time.perf_counter_ns()
    print('Current task: create audio fingerprints.')
    print('Collecting file paths...')
    files = [{'path': str(p)} for p in get_paths(dirs_to_scan)]

    print(f'Done. Files found: {len(files)}.')
    shuffling_start = time.perf_counter_ns()
    random.shuffle(files)
    shuffling_elapsed = (time.perf_counter_ns() - shuffling_start) / 10**9
    print(f'Shuffled in {shuffling_elapsed} s.')

    print('Creating audio fingerprints...')
    files = get_fingerprints(files, profiling)
    print('Done.')

    dump_fingerprints(path_to_dump, files)
    fp_elapsed = (time.perf_counter_ns() - fp_start) / 10**9
    print(f'Task done in {fp_elapsed} s.')


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


def get_correlation(nums_a, nums_b):
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

    if min(len(nums_a), len(nums_b)) < MIN_OVERLAP:
        raise Exception('Overlap too small: %i'
                        % min(len(nums_a), len(nums_b)))

    return get_correlation(nums_a, nums_b)


def cross_correlation(nums_a, nums_b, span, step):
    if span > min(len(nums_a), len(nums_b)):
        # Error checking in main program should prevent us from ever being
        # able to get here.
        raise Exception(
            'span >= sample size: %i >= %i\n'
            % (span, min(len(nums_a), len(nums_b)))
            + 'Reduce span, reduce crop or increase SAMPLE_TIME.'
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
        pair[0]['fingerprint'], pair[1]['fingerprint'], SPAN, STEP,
    )
    max_corr_value, max_corr_index = max_index(correlations)
    max_corr_offset = -SPAN + max_corr_index * STEP
    pair = [
        pair[0]['path'],
        pair[1]['path'],
        max_corr_value,
        max_corr_offset,
    ]
    return pair


def get_quick_correlation(pair):
    correlation = get_correlation(pair[0]['fingerprint'],
                                  pair[1]['fingerprint'])
    return {
        'a': pair[0]['path'],
        'b': pair[1]['path'],
        'corr': correlation,
        'offset': 0,
    }


# TODO: generator??
def calculate_correlations(files, music_data_dir, profiling=False):
    corr_start = time.perf_counter_ns()
    processed_files_path = music_data_dir / 'processed_files.jsonl'
    processed_saves_path = music_data_dir / 'processed_saves.jsonl'
    func_start = datetime.datetime.now()
    print(f'Calculaing correlations started at',
          str_no_microseconds(func_start))

    pairs_expected = (len(files) ** 2 - len(files)) // 2
    pairs_processed = 0
    iteration = 1
    print(f'Expected number of pairs: {pairs_expected:,}')

    if processed_files_path.exists():
        print('Found interrupted process. '
              'Previously processed data will be skipped.')
        files = [file for file in files
                 if file['path'] not in jsonl.load(processed_files_path)]
        pairs_processed = pairs_expected - (len(files) ** 2 - len(files)) // 2
        print(f'Current progress: {pairs_processed/pairs_expected:.0%}')
        iteration = len(jsonl.load(processed_saves_path)) + 1
        

    print(' Iter |    Chunk Size      |   Performance  |'
          '  Elapsed |  End in  | Progress')
    while files:
        pairs_chunk = []
        free_memory = psutil.virtual_memory()[1]
        places_left = min(
            free_memory // BYTES_PER_CORRELATION_PAIR - len(files),
            DUMP_SIZE_LIMIT,
        )
        processed = []
        while places_left > 0 and files:
            chosen_file = files.pop()
            processed.append(chosen_file['path'])
            pairs_chunk.extend([[chosen_file, file] for file in files])
            places_left -= len(files)

        print(f'{iteration:5} | ', end='')
        share = len(pairs_chunk) / pairs_expected
        print(f'{len(pairs_chunk):8} ({share:7.2%}) | ', end='')

        iter_start = datetime.datetime.now()
        if profiling:
            results_chunk = list(map(get_quick_correlation, pairs_chunk))
        else:
            with multiprocessing.get_context('spawn').Pool() as pool:
                results_chunk = pool.map(get_quick_correlation, pairs_chunk)
        elapsed = datetime.datetime.now() - iter_start

        performance = len(results_chunk) / elapsed.seconds
        print(f'{performance:7.0f} corr/s | ', end='')
        print(f'{str_no_microseconds(elapsed):>8} | ', end='')
        pairs_processed += len(results_chunk)

        if profiling:
            results_chunk = [pair for pair in results_chunk]
        else:
            results_chunk = [pair for pair in results_chunk
                             if pair['corr'] > THRESHOLD]
        corrs_path = music_data_dir.joinpath(
            f'correlations_{iteration:03}.jsonl'
        )
        jsonl.dump(results_chunk, corrs_path)  # generator yield here
        #  -> to external saving or sending or analysing or other handling
        # async call or thread for dumping/sending, but not for calculations
        jsonl.dump(processed, processed_files_path, mode='a')
        jsonl.dump([str(corrs_path)], processed_saves_path, mode='a')

        end_in_seconds = (pairs_expected - pairs_processed) / performance
        end_in = datetime.timedelta(seconds=end_in_seconds)
        print(f'{str_no_microseconds(end_in):>8} | ', end='')
        print(f'{pairs_processed / pairs_expected:4.0%}')
        iteration += 1
    
    save_paths = jsonl.load(processed_saves_path)
    for child in music_data_dir.glob('correlations_*.jsonl'):
        if (child.is_file()
            and not str(child) in save_paths):
            child.unlink()

    processed_files_path.unlink(missing_ok=True)
    processed_saves_path.unlink(missing_ok=True)
    func_elapsed = datetime.datetime.now() - func_start
    corr_elapsed = (time.perf_counter_ns() - corr_start) / 10**9
    print(f'Task completed in {str_no_microseconds(func_elapsed)}'
          f'({corr_elapsed} s.)')


def collect_correlations(music_data_dir, profiling=False):
    files = load_fingerprints(music_data_dir)
    print('Total audio fingerprints:', len(files))

    calculate_correlations(files, music_data_dir, profiling)
    print(f'Correlation data saved to "{music_data_dir}".')


def print_correlation(source_path, target_path):
    source_file = calculate_fingerprint({'path': source_path})
    target_file = calculate_fingerprint({'path': target_path})
    corr = cross_correlation(
        source_file['fingerprint'],
        target_file['fingerprint'],
        SPAN,
        STEP,
    )

    print(
        f"len_source = {len(source_file['fingerprint'])},",
        f"len_target = {len(target_file['fingerprint'])}",
    )

    max_corr_index = max_index(corr)
    max_corr_offset = -SPAN + max_corr_index * STEP

    print(
        'max_corr_index = ',
        max_corr_index,
        'max_corr_offset = ',
        max_corr_offset,
    )

    if corr[max_corr_index] > THRESHOLD:
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