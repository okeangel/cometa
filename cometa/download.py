#! /usr/bin/env python3

import os
import pathlib
import time
import datetime
import re
import json

import mutagen.mp3
import mutagen.id3
import yandex_music
import jsbeautifier


USER_TAG_PREFIX = 'sweetall'


def get_download_path(nested_path):
    """Returns the default downloads path for Linux or Windows"""
    if os.name == 'nt':
        import winreg
        sub_key = (r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer'
                    '\Shell Folders')
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            downloads = pathlib.Path(
                winreg.QueryValueEx(key, downloads_guid)[0]
            )
    else:
        downloads = pathlib.Path.home().joinpath('Downloads')
    return downloads.joinpath(nested_path)


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


def get_meta_from_yandex_track(track, client):
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
        tags = mutagen.id3.ID3(user_save_path + file_name + '.mp3')
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
    save_cover(track, file_name, user_save_path)
    tags.add(mutagen.id3.APIC(
        encoding=3, mime='image/jpeg', type=3, desc=u'Cover',
        data=open(user_save_path + file_name + '.jpg', 'rb').read(),
    ))
    
    # save ID3 to content file
    tags.save(user_save_path + file_name + '.mp3')
    # delete temp artwork file
    os.remove(user_save_path + file_name + '.jpg')


def save_track(track_from_yandex: yandex_music.track.track.Track,
               client: yandex_music.client.Client,
               imported: str=None) -> None:
    meta = get_meta_from_yandex_track(track, client=client)
    meta['{}_imported'.format(USER_TAG_PREFIX)] = imported

    # save audio sream to content file
    file_name = convert_to_file_name(
        '{} - {} ({})'.format(
            ', '.join(meta['artists']),
            meta['title_combined'],
            meta['yandex_music_track_id'],
    ))
    save_audio(track, file_name, user_save_path)

    update_id3(meta, file_name, user_save_path, track)

    with open(user_save_path + '_saved_from_yandex_music.txt', 'a+') as file:
        file.write(track.id + '\n')


def load_saved_ids(path_to_saved_ids: pathlib.Path) -> list:
    """Return a list of saved IDs from file"""
    if path_to_saved_ids.is_file():
        return path_to_saved_ids.read_text(encoding='utf-8').split('\n')
    return []


def save_like_tracks(user_token: str,
                     path_to_directory: pathlib.Path,
                     path_to_saved_ids: pathlib.Path) -> None:
    """
    Save tracks from Yandex.Music that the user likes.
    
    Skips those tracks whose Yandex Music ID is in `saved_ids`.
    
    Args:
        user_token: to access Yandex.Music
        path_to_directory: directory where files should be saved
        path_to_save_ids: file where ids are saved
    """
    ya_music = yandex_music.Client(user_token).init()
    saved_ids = load_saved_ids(path_to_saved_ids)

    for item in ya_music.users_likes_tracks():
        if item.id not in saved_ids:
            save_track(item.fetch_track(),
                       ya_music,
                       imported=item.timestamp[:19])


if __name__ == '__main__':
    user_save_directory = '!Cometa'
    user_save_path = get_download_path(user_save_directory)
    print(user_save_path)

    user_yandex_music_oauth_link = (
        'https://oauth.yandex.ru/authorize'
        '?response_type=token'
        '&client_id=23cabbbdc6cd418abb4b39c32c41195d'
    )
    print(user_yandex_music_oauth_link)

    user_yandex_music_token = 'AQAAAAABXPQDAAG8XnMPg_r6L0JCtc_Ehhrs-hA'
    save_like_tracks(user_yandex_music_token,
                     user_save_path,
                     user_save_path / '_saved_from_yandex_music.txt')
