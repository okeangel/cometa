#! /usr/bin/env python3

import json
import time
import os
import re
import datetime

import mutagen.mp3
import mutagen.id3
import yandex_music
import jsbeautifier


USER_TAG_PREFIX = 'sweetall'
USER_YANDEX_MUSIC_OAUTH_LINK = (
    'https://oauth.yandex.ru/authorize'
    '?response_type=token'
    '&client_id=23cabbbdc6cd418abb4b39c32c41195d'
)
USER_YANDEX_MUSIC_TOKEN = 'AQAAAAABXPQDAAG8XnMPg_r6L0JCtc_Ehhrs-hA'
USER_SAVE_DIRECTORY = '!Cometa'

def get_download_path():
    """Returns the default downloads path for Linux or Windows"""
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    else:
        return os.path.join(os.path.expanduser('~'), 'Downloads')


def is_saved(file_path):
    """Check if the file is avaliable
    """
    return os.path.isfile(file_path) and os.path.getsize(file_path) > 0


def convert_to_file_name(
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


def save_audio(track, file_name, path):
    if not is_saved(f"{path}{file_name}.mp3"):
        try:
            track.download(f"{path}{file_name}.mp3", 'mp3', 320)
        except yandex_music.exceptions.InvalidBitrateError:
            track.download(f"{path}{file_name}.mp3")


def save_cover(track, file_name, path):
    if not is_saved(f"{path}{file_name}.jpg"):
        try:
            track.download_cover(f"{path}{file_name}.jpg", size='1000x1000')
        except AttributeError:
            track.download_cover(f"{path}{file_name}.jpg")
        except AttributeError as e:
            print(f"{file_name} failed to download the cover:\n{e}")


def save_meta(track, file_name, path):
    if not is_saved(f"{path}{file_name}.json"):        
        with open(f"{path}{file_name}.txt", 'w+', encoding='utf-8') as file:
            file.write(track.to_json())


def trim_original_mix(text):
    restricted = [' (original mix)']
    if text.lower() == 'original mix':
        return None
    for substr in restricted:
        if text.lower().endswith(substr):
            text = text[:-(len(substr))]
    return text


def get_album_data(track, client):
    albums = []
    for album in track.albums:
        release = {
            'genre': album.genre,
            'labels': [l.name for l in album.labels],
            'track_number': album.track_position.index,
            'tracks_total': album.track_count,
            'volume_number': None,
            'volumes_total': None,
        }

        title = trim_original_mix(album.title)
        if album.version:
            title += ' ({})'.format(album.version)
        release['release_title'] = trim_original_mix(title)

        date = '9999'
        if album.release_date:
            date = album.release_date[:19]
        if date.endswith('T00:00:00'):
            date = date[:10]
        if album.year:
            if str(album.year) < date[:4]:
                date = str(album.year)
        if album.original_release_year:
            if str(album.original_release_year) < date[:4]:
                date = str(album.original_release_year)
        release['release_date'] = date

        volumes = client.albums_with_tracks(album.id).volumes
        if volumes:
            release['volume_number'] = album.track_position.volume
            release['volumes_total'] = len(volumes)
        albums.append(release)
    
    albums.sort(key=lambda x: x['release_date'])
    return albums[0]


def extract_meta(track, client):
    meta = {
        'title': trim_original_mix(track.title),
        'version': track.version,
        'publisher': track.major.name,
        'yandex_music_track_id': track.id,
        'language': None,
        'unsynchronized_lyrics': None,
    }

    supplement = track.get_supplement()
    if supplement.lyrics:
        meta['language'] = supplement.lyrics.text_language
        meta['unsynchronized_lyrics'] = supplement.lyrics.lyrics

    if meta['version']:
        meta['version'] = trim_original_mix(meta['version'])
    meta['artists'] = []
    for name in track.artists_name():
        if not meta['version'] or name not in meta['version']:
            meta['artists'].append(name)

    if meta['version']:
        meta['title_combined'] = '{} ({})'.format(meta['title'],
                                                  meta['version'])
    else:
        meta['title_combined'] = meta['title']

    meta.update(get_album_data(track, client=client))
    return meta


def update_id3(meta, file_name, file_path, track):
    # load ID3 tag from content file
    try:
        tags = mutagen.id3.ID3(USER_SAVE_PATH + file_name + '.mp3')
    except mutagen.id3._util.ID3NoHeaderError as e:
        tags = mutagen.id3.ID3()

    tags.add(mutagen.id3.TIT2(encoding=3, text=meta['title_combined']))
    tags.add(mutagen.id3.TPE1(encoding=3, text=meta['artists']))
    tags.add(mutagen.id3.TPUB(encoding=3, text=meta['publisher']))
    if meta['language']:
        tags.add(mutagen.id3.TLAN(encoding=3, text=meta['language']))
    if meta['unsynchronized_lyrics']:
        tags.add(mutagen.id3.USLT(encoding=3,
                                  text=meta['unsynchronized_lyrics']))
    tags.add(mutagen.id3.TALB(encoding=3, text=meta['release_title']))
    tags.add(mutagen.id3.TDRC(encoding=3, text=meta['release_date']))
    tags.add(mutagen.id3.TDRL(encoding=3, text=meta['release_date']))
    if meta['genre']:
        tags.add(mutagen.id3.TCON(encoding=3, text=meta['genre']))
    tags.add(mutagen.id3.TPUB(encoding=3, text=meta['labels']))
    if meta['track_number']:
        tags.add(mutagen.id3.TRCK(
            encoding=1,
            text='{}/{}'.format(meta['track_number'],
                                meta['tracks_total'])
        ))
    if meta['volume_number']:
        tags.add(mutagen.id3.TPOS(
            encoding=3,
            text='{}/{}'.format(meta['volume_number'],
                                meta['volumes_total'])
        ))
    tags.add(mutagen.id3.TXXX(encoding=3,
                              desc='yandex_music_track_id',
                              text=meta['yandex_music_track_id']))
    tags.add(mutagen.id3.TXXX(
        encoding=3,
        desc='{}_imported'.format(USER_TAG_PREFIX),
        text=meta['{}_imported'.format(USER_TAG_PREFIX)],
    ))

    # add artwork
    save_cover(track, file_name, USER_SAVE_PATH)
    tags.add(mutagen.id3.APIC(
        encoding=3, mime='image/jpeg', type=3, desc=u'Cover',
        data=open(USER_SAVE_PATH + file_name + '.jpg', 'rb').read(),
    ))
    
    # save ID3 to content file
    tags.save(USER_SAVE_PATH + file_name + '.mp3')
    # delete temp artwork file
    os.remove(USER_SAVE_PATH + file_name + '.jpg')


def save_track(track, client, imported=None):
    meta = extract_meta(track, client=client)
    meta['{}_imported'.format(USER_TAG_PREFIX)] = imported

    # save audio sream to content file
    file_name = convert_to_file_name(
        '{} - {} ({})'.format(
            ', '.join(meta['artists']),
            meta['title_combined'],
            meta['yandex_music_track_id'],
    ))
    save_audio(track, file_name, USER_SAVE_PATH)

    update_id3(meta, file_name, USER_SAVE_PATH, track)

    with open(USER_SAVE_PATH + '_saved_from_yandex_music.txt', 'a+') as file:
        file.write(track.id + '\n')


def save_new_tracks_liked():
    ya_music = yandex_music.Client(USER_YANDEX_MUSIC_TOKEN).init()
    try:
        with open(USER_SAVE_PATH + '_saved_from_yandex_music.txt') as file:
            saved = file.read().split('\n')
    except FileNotFoundError:
        saved = []

    for item in ya_music.users_likes_tracks():
        if item.id not in saved:
            save_track(item.fetch_track(), ya_music, imported=item.timestamp[:19])


if __name__ == '__main__':
    USER_SAVE_PATH = get_download_path()
    print(USER_SAVE_PATH)
    print(USER_YANDEX_MUSIC_OAUTH_LINK)
    save_new_tracks_liked()
