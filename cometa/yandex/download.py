#! /usr/bin/env python3

import yandex_music
import jsbeautifier
import json
import time
import os
import re


def not_saved(fpath):  
    return (not os.path.isfile(fpath)) or os.path.getsize(fpath) == 0


def filename(name,
             slash_replace=', ',  # слэш: заменять на минус; используется в идентификаторах документов: типа № 1/2
             quote_replace='',  # кавычки: замены нет - удаляем
             multispaces_replace='\x20',  # множественные пробелы на один пробел
             quotes="""“”«»'\""""  # какие кавычки будут удаляться
             ):
    name = re.sub(r'[/]', slash_replace, name)
    name = re.sub(r'[' + quotes + ']', quote_replace, name)
    name = re.sub(r'\s{2,}', multispaces_replace, name)
    name = re.sub(r'[|*?<>:\\\n\r\t\v]', '', name)  # запрещенные символы в windows
    name = name.strip()
    name = name.rstrip('-')  # на всякий случай
    name = name.rstrip('.')  # точка в конце не разрешена в windows
    name = name.strip()  # не разрешен пробел в конце в windows
    return name


# https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d
token = 'AQAAAAABXPQDAAG8XnMPg_r6L0JCtc_Ehhrs-hA'

path = 'E:/Downloads/!Cometa'

ym = yandex_music.Client(token).init()

likes_tracks = ym.users_likes_tracks()

for i in range(len(likes_tracks)):
    track = likes_tracks[i].fetch_track()

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
        name = f'{artists} - {track.title} ({track.version}) ({track.id})'
    else:
        name = f'{artists} - {track.title} ({track.id})'
    fname = filename(name)

    restricted = []

    if (not_saved(f'{path}/{fname}.mp3')
        or not_saved(f'{path}/{fname}.jpg')
        or not_saved(f'{path}/{fname}.txt')
        ):
        print(fname)
        try:
            track.download(f'{path}/{fname}.mp3', 'mp3', 320)
        except yandex_music.exceptions.InvalidBitrateError:
            track.download(f'{path}/{fname}.mp3')
        except yandex_music.exceptions.UnauthorizedError:
            restricted.append(name)

        try:
            track.download_cover(f'{path}/{fname}.jpg', size='1000x1000')
        except AttributeError:
            print(f'{fname} failed to download the cover')
        with open(f'{path}/{fname}.txt', 'w+', encoding='utf8') as file:
            file.write(jsbeautifier.beautify(str(track)))

    with open('!restricted.txt', 'w+') as file:
        file.write('\n'.join(restricted))
