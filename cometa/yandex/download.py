#! /usr/bin/env python3

from yandex_music import Client
import jsbeautifier


token = 'AQAAAAABXPQDAAG8XnMPg_r6L0JCtc_Ehhrs-hA'

ym = Client(token).init()

# https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d


likes_tracks = ym.users_likes_tracks()
# for track in likes_tracks:
track = likes_tracks[0]
track.fetch_track().download('example.mp3', 'mp3', 320)
