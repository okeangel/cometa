import pathlib

import config
import jsonl


def deep_check_identity_fingerprints(ref_path, test_path):
    # Load reference
    ref = jsonl.load(ref_path)
    ref_d = {
        str(item['path']): {
            'chp_fingerprint': item['chp_fingerprint'],
        } for item in ref
    }
    assert len(ref_d) == len(ref)
    del ref

    # Load testing datasets
    test_file_path = test_path
    test = jsonl.load(test_file_path)
    test_d = {
        str(item['path']): {
            'chp_fingerprint': item['chp_fingerprint'],
        } for item in test
    }
    assert len(test_d) == len(test)
    del test

    # Identity check
    assert len(test_d) == len(ref_d)
    for path, file in test_d.items():
        assert path in ref_d
        assert file['chp_fingerprint'] == ref_d[path]['chp_fingerprint']
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
    ref_d = {frozenset([x[0], x[1]]): x[2] for x in ref}
    assert len(ref_d) == len(ref)
    del ref

    # Load testing datasets
    test = []
    for child in test_paths:
        test.extend(jsonl.load(child))
    test_d = {frozenset([x[0], x[1]]): x[2] for x in test}
    assert len(test_d) == len(test)
    del test

    # Identity check
    assert len(test_d) == len(ref_d)
    for pair in test_d:
        assert pair in ref_d
        # assert abs(test_d[pair] - ref_d[pair]) < 0.0000000000000003
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


if __name__ == '__main__':
    userdata_path, localdata_path = config.get_data_paths()
    music_dirs, music_data_dir = config.get_config(userdata_path)

    check_results_correct(music_data_dir)