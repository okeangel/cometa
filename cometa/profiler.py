import cProfile
import pathlib

import config
import fingerprint
import test_fingerprint


if __name__ == '__main__':
    config_dir, local_data_dir = config.get_data_paths()
    music_dirs, music_data_dir = config.get_profile_from_config(
        config_dir / 'config' / 'main.ini', 'test')

    cProfile.run(
        """
fingerprint.collect_fingerprints(
    music_dirs,
    music_data_dir,
    profiling=True,
)
        """, 'fingerprint_collect_fingerprints.pstats')

    cProfile.run(
        """
fingerprint.collect_correlations(
    music_data_dir,
    profiling=True,
)
        """, 'fingerprint_collect_correlations.pstats')

    test_fingerprint.check_results_correct(music_data_dir)
    # добавить проверку корреляций - генерим с определённым сидом,
    # а результаты проверяем по сохранённому коду первого образца