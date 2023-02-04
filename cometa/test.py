import time
import numpy
import random
import csv

import fingerprint as ref

# ----- mock getters -----

def mock_sample(bit_length):
    return random.getrandbits(bit_length)


def mock_fingerprint(power_of_10):
    deviation = numpy.random.randn() * 6 ** power_of_10
    fingerprint_len = round(10 ** power_of_10 + deviation)
    return [mock_sample(32) for _ in range(fingerprint_len)]


def mock_tuple_pair(power_of_10):
    return mock_fingerprint(power_of_10), mock_fingerprint(power_of_10)


def mock_pairs_of_samples(power_of_10):
    return [s for s in zip(*mock_tuple_pair(power_of_10))]


def mock_dict_pair(power_of_10):
    first = {'chp_fingerprint': mock_fingerprint(power_of_10),
             'path': '/mocking/path'}
    second = {'chp_fingerprint': mock_fingerprint(power_of_10),
             'path': '/mocking/path'}
    return first, second


def mock_tuple_pairs(power_of_10):
    return [mock_tuple_pair(3) for _ in range(10 ** power_of_10)]


def mock_dict_pairs(power_of_10):
    return [mock_dict_pair(3) for _ in range(10 ** power_of_10)]

def mock_files(num_of_files):
    return [{'chp_fingerprint': mock_fingerprint(3),
             'path': f'/mocking/path/{i}'} for i in range(num_of_files)]

# ----- A/B performance test -----

def fix(num):
    return str(num)[:8].ljust(8)


def median(seq):
    row = sorted(seq)
    i, r = divmod(len(row), 2)
    if r:
        return row[i]
    return (row[i-1] + row[i]) / 2


def run_test(func, items, timer):
    start = time.time()
    result = [func(*item) for item in items]
    elapsed = time.time() - start
    timer += elapsed
    line = f'{fix(timer)} ({fix(elapsed)}) | '
    return result, elapsed, timer, line


def ab_test(func_a, func_b, mock_getter, cycles=100):
    path = r'C:\Users\okean\OneDrive\test'

    total_a = 0
    total_b = 0
    timings = []

    pad_i = len(str(cycles))
    pad_s = '10.6f'
    pre = ' ' * pad_i
    headline = [pre, 'A: total (elapsed) ', 'B: total (elapsed) ',
                'Speed Up mean/median']
    print(' | '.join(headline))

    for i in range(1, cycles + 1):
        items = mock_getter()

        print(f'{i:{pad_i}} | ', end='')

        if i % 2:
            result_a, elapsed_a, total_a, line_a = run_test(func_a, items, total_a)
            result_b, elapsed_b, total_b, line_b = run_test(func_b, items, total_b)
        else:
            result_b, elapsed_b, total_b, line_b = run_test(func_b, items, total_b)
            result_a, elapsed_a, total_a, line_a = run_test(func_a, items, total_a)

        print(line_a + line_b + f'{total_a / total_b - 1:6.2%}', end='')

        timings.append([elapsed_a, elapsed_b])

        median_a = median([i[0] for i in timings])
        median_b = median([i[1] for i in timings])
        print(f' / {median_a / median_b - 1:6.2%}')

        if result_a != result_b:
            print('Returns not equal!')
            print(result_a[0])
            print(result_b[0])
            break

    print(f'Mean speed up: {total_a / total_b:.2f}x = '
          f'{fix(total_a)}, {fix(total_b)}')

    median_a = median([i[0] for i in timings])
    median_b = median([i[1] for i in timings])

    print(f'Median speed up: {median_a / median_b:.2f}x = '
          f'{fix(median_a)}, {fix(median_b)}')

    with open('ab_test.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(timings)

# ----- objects to test -----

def count_xor_oneline(a, b):
    return (a ^ b).bit_count()

# ----- run point -----

if __name__ == '__main__':
    ab_test(  # 
        lambda nums_a, nums_b: sum(
            [(x ^ y).bit_count() for x, y in zip(nums_a, nums_b)]
        ),
        lambda nums_a, nums_b: sum(
            [(x ^ y).bit_count() for x, y in zip(nums_a, nums_b)]
        ),
        lambda: mock_tuple_pairs(4),
    )
