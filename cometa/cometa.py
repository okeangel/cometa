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


    userdata_path, localdata_path = config.get_data_paths()
    music_dirs, music_data_dir = config.get_config(userdata_path)
    print('Music files stored in:')
    print('\n'.join(str(d) for d in music_dirs))
    print(f'...and music data will read and write in:\n{music_data_dir}')

    print('Do you want to create new fingerprints?\n'
          '(type "y" otherwise task will be skipped)')
    if input().lower() in ['y', 'yes']:
        fingerprint.collect_fingerprints(music_dirs, music_data_dir)

    print('Do you want to overview collected fingerprints?\n'
          '(type "y" otherwise task will be skipped)')
    if input().lower() in ['y', 'yes']:
        fingerprint.overview_audio_files(music_data_dir)

    print('Do you want to calculate correlations?\n'
          '(type "y" otherwise task will be skipped)')
    if input().lower() in ['y', 'yes']:
        fingerprint.collect_correlations(music_data_dir)

    print('Well done. Have a nice day!')