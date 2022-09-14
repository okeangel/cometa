#! /usr/bin/env python3

import json
import time
import os
import re

import mutagen
import yandex_music
import jsbeautifier


def is_saved(fpath):
    """Check if the file is avaliable
    """
    return os.path.isfile(fpath) and os.path.getsize(fpath) > 0


def create_name_for_file(
        name,
        slash_replace=', ',
        multispaces_replace='\x20',
        quote_replace='',
        quotes="""“”«»'\"""",  # какие кавычки будут удаляться
    ):
    name = re.sub(r'[/]', slash_replace, name)
    name = re.sub(r'[' + quotes + ']', quote_replace, name)
    name = re.sub(r'\s{2,}', multispaces_replace, name)

    # запрещенные символы в windows
    name = re.sub(r'[|*?<>:\\\n\r\t\v]', '', name)

    name = name.strip()
    name = name.rstrip('-')  # на всякий случай
    name = name.rstrip('.')  # точка в конце не разрешена в windows
    name = name.strip()  # не разрешен пробел в конце в windows
    return name

dir_path = "E:\\YandexDisk\\DJ Full Tracks\\Style - Epic Trance\\"
file_name = "Airbase - Escape.flac"
for i in mutagen.File(dir_path + file_name).items():
    print(i)

oauth_link = "https://oauth.yandex.ru/authorize" \
             "?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d"
token = 'AQAAAAABXPQDAAG8XnMPg_r6L0JCtc_Ehhrs-hA'
path = 'E:/Downloads/!Cometa'

ya_music = yandex_music.Client(token).init()

restricted = []
for item in ya_music.users_likes_tracks()[:3]:
    track = item.fetch_track()

    version = track.version

    artists = []
    for name in track.artists_name():
        if not version or name not in version:
            artists.append(name)
    artists = ', '.join(artists)
    if version and version.startswith('feat'):
        artists += ' ' + version
        version = None

    if version:
        title_with_version = f'{track.title} ({track.version})'
    else:
        title_with_version = track.title

    file_name = create_name_for_file(
        f'{artists} - {title_with_version} ({track.id})'
    )
    if len(track.albums) > 0:
        print(file_name)
        # print(jsbeautifier.beautify(str(track)))
        for a in track.albums:
            # print(a.track_count)
            date = a.release_date[:10]
            if a.original_release_year and a.original_release_year < date[:4]:
                date = a.original_release_year
            labels = str([l.name for l in a.labels]).strip('[').strip(']')
            print(f'{a.title} ({a.version}) at {date} by {labels}')
        print(a.cover_uri)

        print()
    if not is_saved(f'{path}/{file_name}.mp3'):
        try:
            track.download(f'{path}/{file_name}.mp3', 'mp3', 320)
        except yandex_music.exceptions.InvalidBitrateError:
            track.download(f'{path}/{file_name}.mp3')
        except yandex_music.exceptions.UnauthorizedError:
            restricted.append(name)

    if not is_saved(f'{path}/{file_name}.jpg'):
        try:
            track.download_cover(f'{path}/{file_name}.jpg', size='1000x1000')
        except AttributeError:
            print(f'{file_name} failed to download the cover')

    if not is_saved(f'{path}/{file_name}.txt'):        
        with open(f'{path}/{file_name}.txt', 'w+', encoding='utf-8') as file:
            file.write(
                jsbeautifier.beautify(str(track))
            )

with open('!restricted.txt', 'w+') as file:
    file.write('\n'.join(restricted))
