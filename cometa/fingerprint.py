import pathlib
import psutil
import subprocess
import multiprocessing
import random

import time
import datetime
import tqdm
import gmpy2

import jsonl


# fpcalc uses fixed fingerprint sample size and frequency
BITS_PER_SAMPLE=32
SAMPLES_PER_SECOND = 8

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
# 1% of best matches has correlation greater than 0.577 on 83k tracks
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


def fix(num, width=9):
    return str(num)[:width].ljust(width)


def str_no_microseconds(elapsed):
    return str(elapsed).split('.')[0]

# -------------------- fingerprint --------------------

def calculate_fingerprint(file, length=SAMPLE_TIME):
    try:
        fpcalc_out = subprocess.getoutput(
            'fpcalc -raw -length %i "%s"'
            % (
                length,
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
    file['duration'] = duration
    file['fingerprint'] = fingerprint
    return file


def get_fingerprints(files, length=SAMPLE_TIME, profiling=False):
    if profiling:
        tasks = map(calculate_fingerprint, files)
        results = [result for result in tqdm.tqdm(tasks, total=len(files))]
    else:
        pool = multiprocessing.Pool()
        tasks = pool.imap_unordered(calculate_fingerprint, files)
        results = [result for result in tqdm.tqdm(tasks, total=len(files))]

    files = [file for file in results if file['fingerprint']]
    files.sort(key=lambda x: len(x['fingerprint']))
    return files


def get_paths(basic_paths):
    paths = []
    for dir in basic_paths:
        for p in dir.rglob('*'):
            if p.is_file():
                paths.append(p)
    return paths


def collect_fingerprints(dirs_to_scan,
                         music_data_dir,
                         profiling=False,
                         frame_time=SAMPLE_TIME,
                         frame_align='head'):
    fp_start = time.perf_counter_ns()
    print('Current task: create audio fingerprints.')
    print('Collecting file paths... ', end='')
    files = [{'path': str(p)} for p in get_paths(dirs_to_scan)]
    print(f'Done. Files found: {len(files)}.')
    random.shuffle(files)

    print('Creating audio fingerprints.')
    files = get_fingerprints(files, length=frame_time, profiling=profiling)

    print('Saving fingerprints...')
    dump_path = music_data_dir.joinpath('fingerprints')
    jsonl.dump(files, dump_path)
    print(f'Audio fingerprints saved to "{dump_path}".')

    fp_elapsed = (time.perf_counter_ns() - fp_start) / 10**9
    print(f'Task done in {fp_elapsed} s.')

# -------------------- fingerprint overview --------------------

def count_extentions(paths):
    exts = {}
    for p in paths:
        ext = p.suffix
        if ext in exts.keys():
            exts[ext] += 1
        else:
            exts[ext] = 1
    return exts


def overview_audio_tracks(music_data_dir):
    dump_path = music_data_dir.joinpath('fingerprints')
    tracks = jsonl.load(dump_path)
    paths = [pathlib.Path(track['path']) for track in tracks]
    print('Audio detected in files with extentions:')
    print(count_extentions(paths))

    music_exts = ['.mp3', '.flac', '.m4a', '.ogg', '.mka', '.wma']
    unexpected_files = [
        path for path in paths if path.suffix not in music_exts
    ]
    if unexpected_files:
        print('Files with unexpected audio:')
        [print(path) for path in unexpected_files]

# -------------------- correlation --------------------

def truncate_xmpz(fpz_a, bit_length_b):
    return fpz_a[: bit_length_b]


def get_xmpz_correlation(fpz_a, bit_length_a, fpz_b, bit_length_b):
    """Return correlation between lists of numbers"""

    if fpz_a == 0 or fpz_b == 0:
        # Error checking in main program should prevent us from ever being
        # able to get here.
        raise ValueError('Empty lists cannot be correlated.')

    #if isinstance(fpz_a, gmpy2.mpz):
    if bit_length_a == bit_length_b:
        bits_different = gmpy2.hamdist(fpz_a, fpz_b)
    elif bit_length_a > bit_length_b:
        bits_different = gmpy2.hamdist(
            truncate_xmpz(fpz_a, bit_length_b),
            fpz_b,
        )
    else:
        raise ValueError('Fingerprint B longer than A')

    return 1 - bits_different / bit_length_b


def get_ref_correlation(nums_a, nums_b):
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

    bits_total = len(nums_a) * BITS_PER_SAMPLE
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

    return get_ref_correlation(nums_a, nums_b)


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


def get_quick_ref_correlation(pair):
    correlation = get_ref_correlation(pair[0]['fingerprint'],
                                      pair[1]['fingerprint'])
    return {
        'a': pair[0]['path'],
        'b': pair[1]['path'],
        'corr': correlation,
    }


def get_quick_xmpz_correlation(pair):
    correlation = get_xmpz_correlation(pair[0]['xmpz_fingerprint'],
                                       pair[0]['frame_bit_lenght'],
                                       pair[1]['xmpz_fingerprint'],
                                       pair[1]['frame_bit_lenght'])
    return {
        'a': pair[0]['path'],
        'b': pair[1]['path'],
        'corr': correlation,
    }


def get_quick_combi_correlation(pair):
    bit_length_a = pair[0]['frame_bit_lenght']
    bit_length_b = pair[1]['frame_bit_lenght']

    if bit_length_a == bit_length_b:
        method = 'mpz'
        bits_different = gmpy2.hamdist(pair[0]['mpz_fingerprint'],
                                       pair[1]['mpz_fingerprint'])
        correlation = 1 - bits_different / bit_length_a
    else:
        method = 'ref'
        correlation = get_ref_correlation(pair[0]['fingerprint'],
                                          pair[1]['fingerprint'])

    return {
        'a': pair[0]['path'],
        'b': pair[1]['path'],
        'corr': correlation,
        'method': method,
    }


# TODO: generator??
def calculate_correlations(tracks,
                           music_data_dir,
                           method='ref',
                           threshold=0,
                           profiling=False,
                           debug=False):

    calc_corr_start = time.perf_counter_ns()

    print(f'Calculaing correlations started at '
          f'{str_no_microseconds(datetime.datetime.now())}'
          f', method is: {method}.')

    # select correlation implementation

    jobs = {
        'combi': get_quick_combi_correlation,
        'ref': get_quick_ref_correlation,
        'xmpz': get_quick_xmpz_correlation,
    }
    if method in jobs:
        job = jobs[method]
    else:
        raise ValueError(f'Unknown method: {method}.')

    # inititalize counters

    iteration = 1
    pairs_processed = 0
    pairs_expected = (len(tracks) ** 2 - len(tracks)) // 2
    handicap = 0
    print(f'Expected number of pairs: {pairs_expected:,}.')

    # detect for files of previous processes

    processed_tracks_path = music_data_dir / 'processed_tracks.jsonl'
    processed_dumps_path = music_data_dir / 'processed_dumps.jsonl'
    processed_elapsed_path = music_data_dir / 'processed_elapsed.jsonl'

    detection_start = time.perf_counter_ns()
    if processed_tracks_path.exists():
        # previous calculation was interrupted but saved its progress
        print('Found interrupted process. '
              'Previously processed data will be skipped.')

        # update tracks to saved state
        tracks = [track for track in tracks
                 if track['path'] not in jsonl.load(processed_tracks_path)]

        # update counters to saved state
        iteration = len(jsonl.load(processed_dumps_path)) + 1
        pairs_processed = (pairs_expected
                           - (len(tracks) ** 2 - len(tracks))
                              // 2)
        handicap = pairs_processed
        print(f'Current progress: {pairs_processed/pairs_expected:.0%}')
    else:
        # remove previous results as garbage
        for child in music_data_dir.glob('correlations*.jsonl'):
            if child.is_file():
                child.unlink()
    detection_elapsed = (time.perf_counter_ns() - detection_start) / 10**9
    print(f'Previous results detection finished in '
          f'{fix(detection_elapsed)} s.')

    # start process in a loop

    print(' Iter |    Chunk Size      |   Performance  |'
          '  Elapsed  |  End in  | Progress')
    while tracks:

        # TODO: define iteration as function

        iter_start = time.perf_counter_ns()
        print(f'{iteration:5}', end=' | ')

        # set how much pairs need to create for best performance

        free_memory = psutil.virtual_memory()[1]
        places_left = min(
            free_memory // BYTES_PER_CORRELATION_PAIR - len(tracks),
            DUMP_SIZE_LIMIT,
        )
        if profiling or debug:
            places_left = min(places_left, pairs_expected // 3)

        # create a batch for a job

        batching_start = time.perf_counter_ns()
        batch = []
        processed = []
        while places_left > 0 and tracks:
            chosen_track = tracks.pop()
            batch.extend([[chosen_track, track]
                                 for track in reversed(tracks)])
            processed.append(chosen_track['path'])
            places_left -= len(tracks)
        batch_size = len(batch)
        batching_elapsed = (time.perf_counter_ns() - batching_start) / 10**9

        share = batch_size / pairs_expected
        print(f'{batch_size:8} ({share:7.2%})', end=' | ')

        # calculate correlations in the batch

        batch_corr_start = time.perf_counter_ns()
        if profiling:
            results_chunk = list(map(job, batch))
        else:
            with multiprocessing.Pool() as pool:
                results_chunk = pool.map(job, batch)
        batch_corr_elapsed = (time.perf_counter_ns()
                              - batch_corr_start) / 10**9

        performance = batch_size / batch_corr_elapsed
        print(f'{performance:7.0f} corr/s', end=' | ')
        print(f'{fix(batch_corr_elapsed)}', end=' | ')

        # filter batch results

        if threshold:
            results_chunk = [pair for pair in results_chunk
                             if pair['corr'] > threshold]

        # dump batch result

        dumping_start = time.perf_counter_ns()
        if threshold:
            file_name = 'correlations_filtered.jsonl'
            mode = 'a'
        else:
            file_name = f'correlations_all_{iteration:04}.jsonl'
            mode = 'w'
        corrs_path  = music_data_dir / file_name
        # if generator then yield here to return result
        # to save, send, handle
        # TODO: async dumping
        jsonl.dump(results_chunk, corrs_path, mode=mode)
        dumping_elapsed = (time.perf_counter_ns() - dumping_start) / 10**9

        # freeze progress

        jsonl.dump(processed, processed_tracks_path, mode='a')
        jsonl.dump([str(corrs_path)], processed_dumps_path, mode='a')
        
        # update counters

        iteration += 1
        pairs_processed += batch_size

        # progress indication

        iter_elapsed = (time.perf_counter_ns() - iter_start) / 10**9
        end_in_seconds = ((pairs_expected - pairs_processed) * iter_elapsed
                          / batch_size)                          
        end_in = datetime.timedelta(seconds=end_in_seconds)
        print(f'{str_no_microseconds(end_in):>8}', end=' | ')
        print(f'{pairs_processed / pairs_expected:4.0%}', end=' | ')

        # perf_couters indication

        parts = [batching_elapsed, batch_corr_elapsed, dumping_elapsed]
        other_elapsed = iter_elapsed - sum(parts)
        parts.append(other_elapsed)

        print(f'i: {fix(iter_elapsed)}', end=' = ')
        print(f'b: {fix(batching_elapsed)}', end=' + ')
        print(f'c: {fix(batch_corr_elapsed)}', end=' + ')
        print(f'd: {fix(dumping_elapsed)}', end=' + ')
        print(f'o: {fix(other_elapsed)}')
        
        jsonl.dump(parts, processed_elapsed_path, mode='a')
        

    for child in music_data_dir.glob('correlations_*.jsonl'):
        if (child.is_file()
            and not str(child) in jsonl.load(processed_dumps_path)):
            child.unlink()

    processed_tracks_path.unlink(missing_ok=True)
    processed_dumps_path.unlink(missing_ok=True)
    calc_corr_elapsed = (time.perf_counter_ns() - calc_corr_start) / 10**9
    calc_corr_timedelta = datetime.timedelta(seconds=calc_corr_elapsed)
    mean_performance = (pairs_processed - handicap) / calc_corr_elapsed
    print(f'Task completed in {str_no_microseconds(calc_corr_timedelta)}'
          f' ({calc_corr_elapsed} s)'
          f' with mean performance {mean_performance} corr/s'
          ' (excluding results restored from save).')


def mpz_bitarray(nums, item_bit_lenght):
    long = 0
    for x in reversed(nums):
        long <<= item_bit_lenght
        long += x
    return gmpy2.mpz(long)  # try to move to 1st line


def get_frame(track, frame_time, frame_align):
    fingerprint_len = len(track['fingerprint'])
    frame_len = frame_time * SAMPLES_PER_SECOND

    if frame_align == 'middle':
        diff = fingerprint_len - frame_len
        if diff > 0:
            padding, appendix = divmod(diff, 2)
            frame = track['fingerprint'][padding: -padding - appendix]
        else:
            frame = track['fingerprint']
    elif frame_align == 'head':
        frame = track['fingerprint'][:frame_len]
    else:
        raise ValueError(f'Unknown frame alignement: {method}.')

    frame_bit_lenght = min(frame_len, fingerprint_len) * BITS_PER_SAMPLE
    mpz_fp = mpz_bitarray(frame, BITS_PER_SAMPLE)

    return {
        'path': track['path'],
        'fingerprint': frame,
        'mpz_fingerprint': mpz_fp,
        'xmpz_fingerprint': gmpy2.xmpz(mpz_fp),
        'frame_bit_lenght': frame_bit_lenght,
        'frame_time': frame_time,
        'frame_align': frame_align,
    }



def collect_correlations(music_data_dir,
                         frame_time=SAMPLE_TIME,
                         frame_align='head',
                         method='combi',
                         threshold=0,
                         profiling=False,
                         debug=False):

    start_loading = time.perf_counter_ns()
    dump_path = music_data_dir.joinpath('fingerprints')
    print(f'Loading from "{dump_path}"...')
    tracks = jsonl.load(dump_path)
    elapsed_loading = (time.perf_counter_ns() - start_loading) / 10 ** 9
    print(f'{len(tracks)} audio fingerprints'
          f' loaded in {fix(elapsed_loading)} s.')

    start_framing = time.perf_counter_ns()
    frames = [get_frame(track, frame_time, frame_align) for track in tracks]
    elapsed_framing = (time.perf_counter_ns() - start_framing) / 10 ** 9
    print(f'Fingerprints framed in {fix(elapsed_framing)} s.')

    calculate_correlations(frames,
                           music_data_dir,
                           method=method,
                           threshold=threshold,
                           profiling=profiling,
                           debug=debug)

    print(f'Correlation data saved to "{music_data_dir}".')


def print_correlation(ref_path, test_path, length=SAMPLE_TIME):
    ref_track = calculate_fingerprint({'path': ref_path}, length=length)
    test_track = calculate_fingerprint({'path': test_path}, length=length)
    corr = cross_correlation(
        ref_track['fingerprint'],
        test_track['fingerprint'],
        SPAN,
        STEP,
    )

    print(
        f"len_source = {len(ref_track['fingerprint'])},",
        f"len_target = {len(test_track['fingerprint'])}",
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
                    ref_path,
                    test_path,
                    corr[max_corr_index],
                    max_corr_offset,
                )
            )
        )
    else:
        print('No statistically significant correlation was found.')