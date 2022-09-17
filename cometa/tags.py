import mutagen.mp3
import mutagen.id3
import os
import json
import jsbeautifier


def save_tags_from_dir(dir_path):
    text = []
    for (dirpath, dirnames, filenames) in os.walk(dir_path):
        for name in filenames:
            audio_file = mutagen.File(dirpath + name)
            text.append(f'\n    {str(name)}\n')
            try:
                text.append(audio_file.info.pprint())
            except AttributeError as e:
                text.append(str(e))
            text.append('')
            text.append(jsbeautifier.beautify(str(audio_file)))
            text.append(str('- ' * 40 + '\n\n'))

    with open(dir_path + '_output.txt', 'w', encoding='utf-8') as file:
        file.write('\n'.join(text))


def read(file_path):
    track = mutagen.File(file_path)
    print(' ' * 4 + 'mutagen.File("'+ file_path + '")\n')
    track.pprint()
    print(jsbeautifier.beautify(str(track)))
    print(track.info)
    print(track.info.length)
    print(track.info.bitrate)
    print('- ' * 40 + '\n')
    #track.save()


def save_vorbis_title(track_file_path, title):
    track = mutagen.File(track_file_path)
    track['title'] = title
    track.save()


def write_tag(filename, tags: dict):
    # 3 is for utf-8
    # image/jpeg or image/png
    # 3 is for the cover image
    d = {
        'isrc': TSRC,
        'title': mutagen.id3.TIT2(encoding=3, text=value),
        'subtitle': TIT3,
        'year': TYER,
        'date': TYER,
        'yandex_music_track_id': TXXX,
        'original_release_year': TORY,
        'album': mutagen.id3.TALB(encoding=3, text=value),
        'track_number': mutagen.id3.TRCK(encoding=3, text=value),
        'publisher': TPUB,
        'track_artist': mutagen.id3.TPE1(encoding=3, text=value),
        'album_artist': None,
        'band': mutagen.id3.TPE2(encoding=3, text=value),
        'lyrics': SYLT,
        'comment': mutagen.id3.COMM(
            encoding=3, lang=u'eng', desc='desc', text=value),
        'artwork': mutagen.id3.APIC(
            encoding=3, mime='image/jpeg', type=3, desc=u'Cover',
            data=open('image.jpg', 'rb').read(),
        ),
    }
    track = mutagen.id3.ID3(track_file_path, translate=False)
    for tag in tags:
        track.add(mutagen.id3.TIT2(encoding=3, text=title))
    track.save(v2_version=3)


# When you assign text strings, we strongly recommend using
# Python unicode objects rather than str objects. If you use str objects,
# Mutagen will assume they are in UTF-8.

# Most tag formats support multiple values for each key,
# so when you access them you will get a list of strings.
# Similarly, you can assign a list of strings rather than a single one.

# Vorbis, FLAC, APEv2 - same structure

test_path = "F:\\mutagen\\"

read(test_path + '1-3.mp3')

metadata = mutagen.id3.ID3(test_path + '1-3.mp3', translate=False)
# v2_version=3
print(metadata.version)
print(jsbeautifier.beautify(str(metadata)))

#metadata.save()
