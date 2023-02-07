import config
import fingerprint
#import argparse


if __name__ == '__main__':
    #parser = argparse.ArgumentParser(
    #    description='Find similar audio files by audio fingerprints.',
    #)
    #parser.add_argument('-i', '--info')

    #args = parser.parse_args()
    #print(args.indir)

    music_dirs, music_data_dir = config.get_config()
    print('Music files stored in:')
    for d in music_dirs:
        print(f'- "{d}"')
    print(f'...and music data will read and write in:\n- "{music_data_dir}"')

    print('Do you want to create new fingerprints?\n'
          '(type "y" otherwise task will be skipped)')
    if input('μ: ').lower() in ['y', 'yes']:
        fingerprint.collect_fingerprints(music_dirs, music_data_dir)

    print('Do you want to overview collected fingerprints?\n'
          '(type "y" otherwise task will be skipped)')
    if input('μ: ').lower() in ['y', 'yes']:
        fingerprint.overview_audio_files(music_data_dir)

    print('Do you want to calculate correlations?\n'
          '(type "y" otherwise task will be skipped)')
    if input('μ: ').lower() in ['y', 'yes']:
        fingerprint.collect_correlations(music_data_dir)

    print('Well done. Have a nice day!')