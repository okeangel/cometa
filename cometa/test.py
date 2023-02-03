import time
import numpy
import random

import fingerprint as ref
import fingerprint2 as test


def mock_fingerprint(n):
    deviation = numpy.random.randn() * 6 ** n
    fingerprint_len = round(10 ** n + deviation)
    return [random.getrandbits(32) for _ in range(fingerprint_len)]


def mock_pair(n):
    first = {'chp_fingerprint': mock_fingerprint(n),
             'path': '/mocking/path'}
    second = {'chp_fingerprint': mock_fingerprint(n),
             'path': '/mocking/path'}
    return first, second


arg = [mock_pair(3) for _ in range(100*150)]
path = r'C:\Users\okean\OneDrive\test'


for i in range(100):

    start_a = time.time()
    return_a = [ref.get_max_correlation(x) for x in arg]
    #return_a = ref.calculate_correlations(arg, path)
    elapsed_a = time.time() - start_a
    print('A', elapsed_a)
    total_a += elapsed_a


    start_b = time.time()
    return_b = [test.get_quick_correlation(x) for x in arg]
    #return_b = ref.calculate_correlations(arg, path)    
    elapsed_b = time.time() - start_b
    print('B', elapsed_b)
    total_b += elapsed_b

    if return_a != return_b:
        print('Returns not equal!')
        break

print('Speed up:', round(total_a / total_b, 2), total_a, total_b)