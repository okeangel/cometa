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
    print(config.APP_NAME, config.APP_VERSION, f'({config.RELEASE_DATE}).')

    music_dirs, music_data_dir = config.get_config()
    print('Music files stored in:')
    for d in music_dirs:
        print(f'- "{d}"')
    print(f'...and music data will read and write in:\n- "{music_data_dir}"')

    print('Do you want to create new fingerprints?\n'
          '(type "y" otherwise task will be skipped)')
    if input('μ: ').lower() in ['y', 'yes']:
        params = {}
        print("""
By default, the fingerprint is built over the entire length of the audio.
If you use not the entire length of the track, but only a part, the accuracy
slightly decrease, but the creation speed will increase.
If you want to limit the length of the print - then specify the desired length
in seconds (for example, 180). Otherwise, just skip the question.
        """.strip())
        frame_time = input('μ: ')
        if frame_time.isdigit():
            params['frame_time'] = int(frame_time)
            print('Do you want to scan the head of tracks or the middle?')
            frame_align = input('Type (h)ead or (m)iddle. μ: ').lower()
            if frame_align in ['h', 'head']:
                params['frame_align'] = 'head'
            elif frame_align in ['m', 'middle']:
                params['frame_align'] = 'middle'

        fingerprint.collect_fingerprints(music_dirs, music_data_dir, **params)

    print('Do you want to overview collected fingerprints?\n'
          '(type "y" otherwise task will be skipped)')
    if input('μ: ').lower() in ['y', 'yes']:
        fingerprint.overview_audio_tracks(music_data_dir)

    print('Do you want to calculate correlations?\n'
          '(type "y" otherwise task will be skipped)')
    if input('μ: ').lower() in ['y', 'yes']:
        params = {}
        print("""
If you analyze not whole tracks, but only fragments of a certain length,
it will come out a little less accurately, but much faster.
Skip the input if you wish to parse the full length.
Otherwise, enter the number of seconds (for example, 180).
        """.strip())
        frame_time = input('μ: ')
        if frame_time.isdigit():
            params['frame_time'] = int(frame_time)
            print('Do you want to compare from the head or in the middle?')
            frame_align = input('Type (h)ead or (m)iddle. μ: ').lower()
            if frame_align in ['h', 'head']:
                params['frame_align'] = 'head'
            elif frame_align in ['m', 'middle']:
                params['frame_align'] = 'middle'
        print("""
Set threshold from 0 (dump all correlations) to 1 (dump only complete matches).
        """.strip())
        threshold = input('μ: ')
        if threshold.replace(".", "", 1).isdigit():
            params['threshold'] = float(threshold)
        fingerprint.collect_correlations(music_data_dir, **params)

    print('Well done. Have a nice day!')