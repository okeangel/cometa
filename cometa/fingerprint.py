import subprocess
import numpy
import pathlib
import multiprocessing
import pickle

import tqdm


# seconds to sample audio file for
sample_time = 500  # number of points to scan cross correlation over
span = 150  # step size (in points) of cross correlation
step = 1  # minimum number of points that must overlap in cross correlation

# exception is raised if this cannot be met
min_overlap = 20  # report match when cross correlation has a peak
                  # exceeding threshold
threshold = 0.0


def calculate_fingerprint(file):
    try:
        fpcalc_out = subprocess.getoutput(
            'fpcalc -raw -length %i "%s"' % (
                sample_time, file['path'],
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
        listx = listx[:len(listy)]  
    elif len(listx) < len(listy):       
        listy = listy[:len(listx)]      

    covariance = 0  
    for i in range(len(listx)):     
        covariance += 32 - bin(listx[i] ^ listy[i]).count("1")  
    covariance = covariance / float(len(listx))
    return covariance/32


def cross_correlation(listx, listy, offset):    
    if offset > 0:      
        listx = listx[offset:]      
        listy = listy[:len(listx)]  
    elif offset < 0:        
        offset = -offset        
        listy = listy[offset:]      
        listx = listx[:len(listy)]

    if min(len(listx), len(listy)) < min_overlap:
        raise Exception('Overlap too small: %i' % min(len(listx), len(listy)))

    # cross correlate listx and listy with offsets from -span to span
    return correlation(listx, listy)  


def compare(listx, listy, span, step):  
    if span > min(len(listx), len(listy)):

    # Error checking in main program should prevent us from ever being      
    # able to get here.     
        raise Exception(
            'span >= sample size: %i >= %i\n' % (
                span, min(len(listx), len(listy))
            ) + 'Reduce span, reduce crop or increase sample_time.'
        )

    corr_xy = []    
    for offset in numpy.arange(-span, span + 1, step):      
        corr_xy.append(cross_correlation(listx, listy, offset))

    # return index of maximum value in list
    return corr_xy


def max_index(listx):   
    max_index = 0   
    max_value = listx[0]    
    for i, value in enumerate(listx):       
        if value > max_value:           
            max_value = value           
            max_index = i   
    return max_index


def get_max_corr(corr, source, target): 
    max_corr_index = max_index(corr)    
    max_corr_offset = -span + max_corr_index * step

    print("max_corr_index = ", max_corr_index,
          "max_corr_offset = ", max_corr_offset)

    if corr[max_corr_index] > threshold:
        print((
            '%s and %s match with correlation of %.4f at offset %i' % (
                source, target, corr[max_corr_index], max_corr_offset
            )
        ))

def correlate(source, target):  
    corr = compare(fingerprint_source, fingerprint_target, span, step)

    print(f'duration_source = {duration_source}, duration_target = {duration_target}')
    print(f'len_source = {len(fingerprint_source)}, len_target = {len(fingerprint_target)}')
    ratio_source = len(fingerprint_source) / duration_source
    ratio_target = len(fingerprint_target) / duration_target
    print(f'ratio_source = {ratio_source}, ratio_target = {ratio_target}')

    get_max_corr(corr, source, target)  


def count_extentions(paths):
    exts = {}
    for p in paths:
        ext = p.suffix
        if ext in exts.keys():
            exts[ext] += 1
        else:
            exts[ext] = 1
    return exts


def get_paths(basic_path):
    paths = []
    for p in basic_path.rglob("*"):
        if p.is_file():
            paths.append(p)
    return paths


def get_fingerprints(files):
    # with multiprocessing.Pool() as pool:
    #     results = pool.map(calculate_fingerprint, files)
    pool = multiprocessing.Pool()
    results = []
    for result in tqdm.tqdm(pool.imap_unordered(calculate_fingerprint, files),
                            total=len(files)):
        results.append(result)
    # pool.close()
    # pool.join()
    # process_bar.close()
    return results


def dump_file_data(path, files):
    with open(path, 'wb') as datafile:
        pickle.dump(files, datafile)


def load_file_data(path):
    with open(path, 'rb') as datafile:
        files = pickle.load(datafile)
    return files


def dump_music_dir_fingerprints(dir_to_scan, path_to_dump):
    print('Collecting file paths...')
    files = [{'path': p} for p in get_paths(dir_to_scan)]
    print(f'Done. Files found: {len(files)}.')

    print('Creating audio fingerprints...')
    files = get_fingerprints(files)
    print('Done.')

    dump_file_data(path_to_dump, files)
    print(f'Audio fingerprints saved to "{path_to_dump}".')
    print('No new tasks. Process terminated.')


def get_pairs(files):
    pairs = []
    pairs_estimate = (len(files)**2) / 2 - len(files)
    print(pairs_estimate)
    for index, file_a in enumerate(files):
        for file_b in files[index:]:
            pairs.append([file_a, file_b])
        print(len(pairs), 'done')
    return pairs


if __name__ == "__main__":
    music_dir = pathlib.Path(r'E:\YandexDisk\music')
    dump_path = pathlib.Path(r'E:\YandexDisk\musicdb\fingerprints.pickle')
    # dump_music_dir_fingerprints(music_dir, dump_path)
    # TODO: experiment with chunksize=pool._pool * 40
    files = load_file_data(dump_path)
    print(len(files))
    print(len(get_pairs(files)))