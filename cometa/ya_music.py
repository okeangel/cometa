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


def save_yandex_track_meta(track_path, track):
    json_path = track_path.with_suffix('.json')
    if not is_saved(json_path):
        json_path.write_text(track.to_json(), encoding='utf-8')


def is_saved(path):
    """Check if the file is avaliable"""
    return path.is_file() and path.stat().st_size > 0


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

    # dot is undesirable because it controls file settings
    name = re.sub(r'\.', '', name)
    # forbidden characters in Windows
    name = re.sub(r'[|*?<>:\\\n\r\t\v]', '', name)

    name = name.strip()
    name = name.rstrip('-')  # на всякий случай
    # name = name.rstrip('.')  # точка в конце не разрешена в windows
    name = name.strip()  # не разрешен пробел в конце в windows
    return name


def trim_original_mix(text):
    restricted = [' (original mix)']
    if text.lower() == 'original mix':
        return None
    for substr in restricted:
        if text.lower().endswith(substr):
            text = text[:-(len(substr))]
    return text


def save_artwork(track, track_path):
    if not is_saved(track_path):
        try:
            track.download_cover(track_path, size='1000x1000')
        except AttributeError:
            track.download_cover(track_path)
        except AttributeError as e:
            print(f"{track_path} failed to download the cover:\n{e}")


def update_id3_artwork(track_path, track):
    artwork_path = track_path.with_suffix('.jpg')
    save_artwork(track, artwork_path)

    track_path = track_path.with_suffix('.mp3')
    try:
        tags = mutagen.id3.ID3(track_path)
    except mutagen.id3._util.ID3NoHeaderError as e:
        tags = mutagen.id3.ID3()
    tags.add(mutagen.id3.APIC(
        encoding=3, mime='image/jpeg', type=3, desc=u'Cover',
        data=artwork_path.read_bytes(),
    ))
    tags.save(track_path)

    # delete temp artwork file
    artwork_path.unlink()


def update_id3(track_path, meta, user_tag_prefix):
    track_path = track_path.with_suffix('.mp3')

    # load ID3 tag from content file
    try:
        tags = mutagen.id3.ID3(track_path)
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
    if meta.get('volume_number'):
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
        desc='{}_imported'.format(user_tag_prefix),
        text=meta['{}_imported'.format(user_tag_prefix)],
    ))

    # save ID3 to content file
    tags.save(track_path)


def save_audio(track, track_path, type='mp3', bitrate=320):
    track_path = track_path.with_suffix('.' + type)
    if not is_saved(track_path):
        try:
            track.download(track_path, type, bitrate)
        except yandex_music.exceptions.InvalidBitrateError:
            track.download(track_path, type)


def complete_with_nines(time_string: str) -> str:
    pattern = '9999-99-99T99:99:99'
    return time_string + pattern[len(time_string):]


def earliest_time_string(time_strings: list) -> str:
    return sorted(time_strings, key=complete_with_nines)[0]


def get_album_meta(albums, track=None):
    album_metas = []
    for album in albums:
        release = {
            'genre': album.genre,
            'labels': [l.name for l in album.labels],
        }

        title = trim_original_mix(album.title)
        if album.version:
            title += ' ({})'.format(album.version)
        release['release_title'] = trim_original_mix(title)

        if(album.start_date):
            print('Start date:', album.start_date)
        dates = ['9999']
        if album.release_date:
            if album.release_date[:19].endswith('T00:00:00'):
                dates.append(album.release_date[:10])
            else:
                dates.append(album.release_date[:19])
        if album.year:
            dates.append(str(album.year))
        if album.original_release_year:
            dates.original_release_year(str(album.year))
        release_date = earliest_time_string(dates)
        release['release_date'] = earliest_time_string(dates)

        release['track_number'] = album.track_position.index
        volumes = album.with_tracks().volumes
        if volumes and len(volumes) > 1:
            if track:
                for volume in volumes:
                    for item in volume:
                        if item.id == track.id:
                            release['tracks_total'] = len(volume)
                            break
                    if release.get('tracks_total'):
                        break
            release['volume_number'] = album.track_position.volume
            release['volumes_total'] = len(volumes)
        else:
            release['tracks_total'] = album.track_count

        album_metas.append(release)
    
    album_metas.sort(key=lambda x: complete_with_nines(x['release_date']))
    return album_metas[0]


def get_track_meta(track):
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

    return meta


def save_track(
        playlist_record: yandex_music.track_short.TrackShort,
        user_tag_prefix: str,
        user_save_path: pathlib.Path,
    ) -> None:
    """Save track with metadata"""
    track = playlist_record.fetch_track()

    meta = get_track_meta(track)
    meta.update(get_album_meta(track.albums, track))
    
    imported_tag_name = '{}_imported'.format(user_tag_prefix)
    meta[imported_tag_name] = playlist_record.timestamp[:19]
    print(meta)

    # save audio stream to content file
    file_name = convert_to_file_name(
        '{} - {} ({})'.format(
            ', '.join(meta['artists']),
            meta['title_combined'],
            meta['yandex_music_track_id'],
    ))
    track_path = user_save_path / file_name
    print(file_name)

    # save_yandex_track_meta(track_path, track)
    save_audio(track, track_path)
    update_id3(track_path, meta, user_tag_prefix)
    update_id3_artwork(track_path, track)

    if not is_saved(user_save_path / (file_name + '.mp3')):
        raise


def load_saved_ids(path_to_saved_ids: pathlib.Path) -> list:
    """Return a list of saved IDs from file"""
    if path_to_saved_ids.is_file():
        return path_to_saved_ids.read_text(encoding='utf-8').split('\n')
    return []


def save_favorite_tracks(
        yandex_music_client: yandex_music.Client,
        user_save_path: pathlib.Path,
        path_to_saved_ids: pathlib.Path,
        user_tag_prefix: str,
    ) -> None:
    """
    Save tracks from Yandex.Music that the user likes.
    
    Skips those tracks whose Yandex Music ID is in `saved_ids`.
    
    Args:
        yandex_music_client: a client with a user session
        user_save_path: directory where files should be saved
        path_to_save_ids: file where ids are saved
        user_tag_prefix: prefix for user custom tags
    """
    saved_ids = load_saved_ids(path_to_saved_ids)

    user_save_path.mkdir(parents=True, exist_ok=True)
    for playlist_record in yandex_music_client.users_likes_tracks():
        if playlist_record.id not in saved_ids:
            save_track(
                playlist_record,
                user_tag_prefix,
                user_save_path,
            )
            with path_to_saved_ids.open('a+') as file:
                file.write(playlist_record.id + '\n')


def get_download_path(nested_path: str) -> pathlib.Path:
    """Return the default downloads path for Linux or Windows"""
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


if __name__ == '__main__':
    user_tag_prefix = 'sweetall'
    print('User tag prefix:', user_tag_prefix + '_*')
    
    user_save_subdir = '!Cometa'
    user_save_path = get_download_path(user_save_subdir)
    print('Download to:', user_save_path)

    user_token = 'AQAAAAABXPQDAAG8XnMPg_r6L0JCtc_Ehhrs-hA'
    yandex_music_client = yandex_music.Client(user_token).init()
    
    save_favorite_tracks(
        yandex_music_client,
        user_save_path,
        user_save_path / '_saved_from_yandex_music.txt',
        user_tag_prefix,
    )