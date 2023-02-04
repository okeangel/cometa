from pycallgraph2 import PyCallGraph
from pycallgraph2.output import GraphvizOutput

import cProfile
import pathlib

import test

import fingerprint


def save_call_graph():
    pair = test.mock_pair(3)

    with PyCallGraph(output=GraphvizOutput()):
        for i in range(10**4):
            fingerprint.get_quick_correlation(pair)


def cycle1(func, arg):
    for i in range(10000):
        map(lambda a, b: (a ^ b).bit_count(), nums_a, nums_b)


if __name__ == '__main__':
    files = test.mock_files(30)
    
    cProfile.run('fingerprint.calculate_correlations(files, pathlib.Path("C:/Users/okean/OneDrive/test"), profiling=True)', 'output.pstats')

    # добавить проверку корреляций - генерим с определённым сидом,
    # а вот результаты придётся проверять по сохранённым