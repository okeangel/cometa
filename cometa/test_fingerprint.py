import cProfile
import pathlib

import config
import jsonl
import fingerprint
import datetime


def deep_check_identity_fingerprints(ref_path, test_path):
    # Load reference
    ref = jsonl.load(ref_path)
    ref_d = {
        str(item['path']): {
            'fingerprint': item['fingerprint'],
        } for item in ref
    }
    assert len(ref_d) == len(ref)
    del ref

    # Load testing datasets
    test_file_path = test_path
    test = jsonl.load(test_file_path)
    test_d = {
        str(item['path']): {
            'fingerprint': item['fingerprint'],
        } for item in test
    }
    assert len(test_d) == len(test)
    del test

    # Identity check
    assert len(test_d) == len(ref_d)
    for path, file in test_d.items():
        assert path in ref_d
        assert file['fingerprint'] == ref_d[path]['fingerprint']
    print('Fingerprint files contain identical data, but different text.')


def check_identity_fingerprints(test_data_dir):
    ref_path = test_data_dir / 'ref_fingerprints.jsonl'
    with open(ref_path, encoding='utf-8') as file:
        ref_text = file.read()

    test_path = test_data_dir / 'fingerprints.jsonl'
    with open(test_path, encoding='utf-8') as file:
        test_text = file.read()

    if test_text != ref_text:
        del ref_text
        del test_text
        deep_check_identity_fingerprints(ref_path, test_path)
    else:
        print('Fingerprint files contain identical text.')

    # Delete test dataset if both are identical
    test_path.unlink()


def deep_check_identity_correlations(ref_path, test_paths):
    ref = jsonl.load(ref_path)
    ref_d = {frozenset([pair['a'], pair['b']]): pair['corr'] for pair in ref}
    assert len(ref_d) == len(ref)
    del ref

    # Load testing datasets
    test = []
    for child in test_paths:
        test.extend(jsonl.load(child))
    test_d = {frozenset([pair['a'], pair['b']]): pair['corr'] for pair in test}
    assert len(test_d) == len(test)
    del test

    # Identity check
    assert len(test_d) == len(ref_d)
    for pair in test_d:
        assert pair in ref_d
        if abs(test_d[pair] - ref_d[pair]) > 0.0000000000000002:
            raise ValueError('Correlation values not identical: '
                f'new {test_d[pair]} != ref {ref_d[pair]}\n'
                f'Pair is: {pair}')
    else:
        print('Correlation files contain identical data, but different text.')


def check_identity_correlations(test_data_dir):
    ref_path = test_data_dir / 'ref_correlations.jsonl'
    with open(ref_path, encoding='utf-8') as file:
        ref_text = file.read()

    test_paths = [path for path in test_data_dir.glob('correlations_*.jsonl')]

    test_text = ''
    for path in test_paths:
        with open(path, encoding='utf-8') as file:
            test_text += file.read()

    if test_text != ref_text:
        del ref_text
        del test_text
        deep_check_identity_correlations(ref_path, test_paths)
    else:
        print('Correlation files contain identical text.')

    # Delete test dataset if both are identical
    [path.unlink() for path in test_paths]


def check_results_correct(music_data_dir):
    check_identity_fingerprints(music_data_dir)
    check_identity_correlations(music_data_dir)


def do_profiling(music_dirs, music_data_dir):
    cProfile.run(
        """
fingerprint.collect_fingerprints(
    music_dirs,
    music_data_dir,
    profiling=True,
)
        """, local_dir / f'{config.APP_VERSION}_fingerprints_{when}.pstats')

    cProfile.run(
        """
fingerprint.collect_correlations(
    music_data_dir,
    profiling=True,
)
        """, local_dir / f'{config.APP_VERSION}_correlations_{when}.pstats')

    check_results_correct(music_data_dir)

def test_correlation_method(music_dirs, music_data_dir, method='ref'):
    if not music_data_dir.joinpath('correlations_001.jsonl').is_file():
        if not music_data_dir.joinpath('fingerprints.jsonl').is_file():
            fingerprint.collect_fingerprints(
                music_dirs,
                music_data_dir,
            )

        fingerprint.collect_correlations(
            music_data_dir,
            method=method,
            profiling=False,
            debug=True,
        )

    check_identity_correlations(music_data_dir)


def test_correlation(music_dirs, music_data_dir):
    for method in ['ref', 'xmpz']:
        test_correlation_method(music_dirs, music_data_dir, method=method)


if __name__ == '__main__':
    roaming_dir, local_dir = config.get_data_paths()
    music_dirs, music_data_dir = config.get_profile_from_config(
        config.get_config_dir() / 'main.ini',
        'test',
    )
    local_dir.mkdir(exist_ok=True, parents=True)

    when = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    test_correlation(music_dirs, music_data_dir)
    if input('Type "y" if you want to run profiling: ').lower() == 'y':
        do_profiling(music_dirs, music_data_dir)
    print('Test OK.')