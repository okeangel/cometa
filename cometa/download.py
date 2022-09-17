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


def is_saved(file_path):
    """Check if the file is avaliable
    """
    return os.path.isfile(file_path) and os.path.getsize(file_path) > 0


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


def save_track(track, file_name, path):
    if not is_saved(f'{path}{file_name}.mp3'):
        try:
            track.download(f'{path}{file_name}.mp3', 'mp3', 320)
        except yandex_music.exceptions.InvalidBitrateError:
            track.download(f'{path}{file_name}.mp3')


def save_cover(track, file_name, path):
    if not is_saved(f'{path}{file_name}.jpg'):
        try:
            track.download_cover(f'{path}{file_name}.jpg', size='1000x1000')
        except AttributeError:
            track.download_cover(f'{path}{file_name}.jpg')
        except AttributeError as e:
            print(f'{file_name} failed to download the cover:\n{e}')


def save_meta(track, file_name, path):
    if not is_saved(f'{path}{file_name}.json'):        
        with open(f'{path}{file_name}.txt', 'w+', encoding='utf-8') as file:
            file.write(track.to_json())


def print_debug_data(track, file_name):
    print(file_name)


def get_album_data(track):
    if len(track.albums) > 0:
        albums = []
        for album in track.albums:
            title = album.title
            if album.version:
                title += f' ({album.version})'

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

            labels = [l.name for l in album.labels]
            dn = None
            if album.volumes and len(album.volumes) > 1:
                dn = f'{album.track_position.volume}/{len(album.volumes)}'
            tn = None
            if album.track_position:
                tn = f'{album.track_position.index}/{album.track_count}'
            
            albums.append({
                'title': title,
                'date': date,
                'genre': album.genre,
                'labels': labels,
                'disc_number': dn,
                'track_number': tn,
            })
        
        albums.sort(key=lambda x: x['date'])
        return albums[0]
    return dict.fromkeys(['title', 'date', 'genre', 'labels',
                          'disc_number', 'track_number'])

def trim_original_mix(text):
    restricted = [' (original mix)']
    for substr in restricted:
        if text.lower().endswith(substr):
            text = text[:-(len(substr))]
    return text


oauth_link = "https://oauth.yandex.ru/authorize" \
             "?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d"
token = 'AQAAAAABXPQDAAG8XnMPg_r6L0JCtc_Ehhrs-hA'
path = 'E:/Downloads/!Cometa/'

ya_music = yandex_music.Client(token).init()
try:
    with open(path + '_saved_from_yandex.music.txt') as file:
        saved = file.read().split('\n')
except FileNotFoundError:
    saved = []

for item in ya_music.users_likes_tracks():
    print(item)
    if item.id in saved:
        continue

    track = item.fetch_track()

    track_version = track.version

    track_artists = []
    track.artists_name()
    if track.artists_name():
        for name in track.artists_name():
            if not track_version or name not in track_version:
                track_artists.append(name)
    else:
        for artist in artists:
            if not track_version or artist.name not in track_version:
                track_artists.append(artist.name)
    if not track_artists:
        track_artists.extend(track.artists_name())
            
            
    track_artists_text = ', '.join(track_artists)
    if track_version and track_version.startswith('feat'):
        track_artists.append(track_version)
        track_artists_text += ' ' + track_version
        track_version = None
    
    if track_version:
        track_title_with_version = f'{track.title} ({track_version})'
    else:
        track_title_with_version = track.title
    track_title_with_version = trim_original_mix(track_title_with_version)

    file_name = create_name_for_file(
        f'{", ".join(track_artists)} - {track_title_with_version} ({track.id})'
    )
    
    print_debug_data(track, file_name)
    save_track(track, file_name, path)

    try:
        tags = mutagen.id3.ID3(path + file_name + '.mp3')
    except mutagen.id3._util.ID3NoHeaderError as e:
        tags = mutagen.id3.ID3()
        print(e)

    liked_dt = item.timestamp[:19]
    created = os.path.getctime(path + file_name + '.mp3')
    created_dt = datetime.datetime.fromtimestamp(created).strftime(
        '%Y-%m-%dT%H:%M:%S.%f')
    created_dt = min([liked_dt, created_dt])
    created_date = created_dt[:10]
    if 'TXXX:CREATED' in tags:
        if created_date > str(tags['TXXX:CREATED']):
            created_date = str(tags['TXXX:CREATED'])            
        del tags['TXXX:CREATED']
        tags.add(mutagen.id3.TXXX(encoding=3,
                                  desc=u'created', text=created_date))
    elif 'TXXX:created' in tags:
        if (created_date < str(tags['TXXX:created'])):
            del tags['TXXX:created']
            tags.add(mutagen.id3.TXXX(encoding=3,
                                      desc=u'created', text=created_date))
    else:
        tags.add(mutagen.id3.TXXX(encoding=3,
                                      desc=u'created', text=created_date))
    tags.add(mutagen.id3.TXXX(encoding=3,
                              desc=u'imported_win_created', text=created_dt))
    tags.add(mutagen.id3.TXXX(encoding=3,
                              desc=u'imported_win_created_unix_ts',
                              text=str(created)))
    
    tags.add(mutagen.id3.TIT2(encoding=3, text=track_title_with_version))
    tags.add(mutagen.id3.TPE1(encoding=3, text=track_artists))
    tags.add(mutagen.id3.TPUB(encoding=3, text=track.major.name))
    unsync_lyrics = track.get_supplement().lyrics
    if unsync_lyrics:
        tags.add(mutagen.id3.USLT(
            encoding=3, text=unsync_lyrics.lyrics))
        if unsync_lyrics.text_language:
            tags.add(mutagen.id3.TLAN(
                encoding=3, text=unsync_lyrics.text_language))
        
    album = get_album_data(track)
    album['title'] = trim_original_mix(album['title'])
    tags.add(mutagen.id3.TALB(encoding=3, text=album['title']))
    tags.add(mutagen.id3.TDRC(encoding=3, text=album['date']))
    tags.add(mutagen.id3.TDRL(encoding=3, text=album['date']))
    if album['genre']:
        tags.add(mutagen.id3.TCON(encoding=3, text=album['genre']))
    tags.add(mutagen.id3.TPUB(encoding=3, text=album['labels']))
    if album['disc_number']:
        tags.add(mutagen.id3.TPOS(encoding=3, text=album['disc_number']))
    if album['track_number']:
        tags.add(mutagen.id3.TRCK(encoding=1, text=album['track_number']))
    tags.add(mutagen.id3.TXXX(encoding=3,
                              desc=u'yandex_music_track_id', text=track.id))
    
    save_cover(track, file_name, path)
    tags.add(mutagen.id3.APIC(
        encoding=3, mime='image/jpeg', type=3, desc=u'Cover',
        data=open(path + file_name + '.jpg', 'rb').read(),
    ))
    
    tags.save(path + file_name + '.mp3')
    os.remove(path + file_name + '.jpg')

    with open(path + '_saved_from_yandex.music.txt', 'a+') as file:
        file.write(track.id + '\n')

    # print('- ' * 40 + '\n\n')
