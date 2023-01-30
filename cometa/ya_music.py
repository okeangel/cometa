#! /usr/bin/env python3

import configparser
import os
import pathlib
import time
import datetime
import re

import mutagen.mp3
import mutagen.id3
import yandex_music


class Config(configparser.ConfigParser):
    def __init__(self):
        super().__init__()
        self.path = pathlib.Path.home().joinpath("yandex_music.ini")
        if self.path.is_file():
            self.read(self.path)
        else:
            self.init()

    def create():
        input(
            """
Сейчас откроется Chrome, а в нём - страница Яндекс.Музыки.
Если страница требует авторизации - то нужно пройти её. Логин, пароль, код,
и всё остальное. Пока не появится главна страница Яндекс.Музыки.
Когда страница музыки полностью появилась - закрывайте браузер,
и Cometa продолжит свою работу.
"""
        )

    def save(self):
        if not "GUI" in self:
            self.add_section("GUI")
        self.set("GUI", "width", str(self.app.winfo_width()))
        self.set("GUI", "height", str(self.app.winfo_height()))
        self.set("GUI", "x", str(self.app.winfo_x()))
        self.set("GUI", "y", str(self.app.winfo_y()))
        with open(self.path, "w+") as configfile:
            self.write(configfile)


def save_yandex_track_meta(track_path, track):
    json_path = track_path.with_suffix(".json")
    if not is_saved(json_path):
        json_path.write_text(track.to_json(), encoding="utf-8")


def is_saved(path):
    """Check if the file is avaliable"""
    return path.is_file() and path.stat().st_size > 0


def convert_to_file_name(
    name,
    slash_replace=", ",
    multispaces_replace="\x20",
    quote_replace="",
    quotes="""“”«»'\"""",  # какие кавычки будут удаляться
):
    name = re.sub(r"[/]", slash_replace, name)
    name = re.sub(r"[" + quotes + "]", quote_replace, name)
    name = re.sub(r"\s{2,}", multispaces_replace, name)

    # dot is undesirable because it controls file settings
    name = re.sub(r"\.", "", name)
    # forbidden characters in Windows
    name = re.sub(r"[|*?<>:\\\n\r\t\v]", "", name)

    name = name.strip()
    name = name.rstrip("-")  # на всякий случай
    # name = name.rstrip('.')  # точка в конце не разрешена в windows
    name = name.strip()  # не разрешен пробел в конце в windows
    return name


def trim_original_mix(text):
    restricted = [" (original mix)"]
    if text.lower() == "original mix":
        return None
    for substr in restricted:
        if text.lower().endswith(substr):
            text = text[: -(len(substr))]
    return text


def save_artwork(track, track_path):
    if not is_saved(track_path):
        try:
            track.download_cover(track_path, size="1000x1000")
        except AttributeError:
            try:
                track.download_cover(track_path)
            except AttributeError as e:
                print(f"{track_path} failed to download the cover:\n{e}")


def update_id3_artwork(track_path, track):
    artwork_path = track_path.with_suffix(".jpg")
    save_artwork(track, artwork_path)

    track_path = track_path.with_suffix(".mp3")
    try:
        tags = mutagen.id3.ID3(track_path)
    except mutagen.id3._util.ID3NoHeaderError as e:
        tags = mutagen.id3.ID3()
    try:
        tags.add(
            mutagen.id3.APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=artwork_path.read_bytes(),
            )
        )
    except FileNotFoundError as e:
        print("Failed to add artwork: {}".format(e))

    tags.save(track_path)

    # delete temp artwork file
    artwork_path.unlink(missing_ok=True)


def update_id3(track_path, meta, user_tag_prefix):
    track_path = track_path.with_suffix(".mp3")

    # load ID3 tag from content file
    try:
        tags = mutagen.id3.ID3(track_path)
    except mutagen.id3._util.ID3NoHeaderError as e:
        tags = mutagen.id3.ID3()

    tags.add(mutagen.id3.TIT2(encoding=3, text=meta["title_combined"]))
    tags.add(mutagen.id3.TPE1(encoding=3, text=meta["artists"]))
    if meta["language"]:
        tags.add(mutagen.id3.TLAN(encoding=3, text=meta["language"]))
    if meta["unsynchronized_lyrics"]:
        tags.add(
            mutagen.id3.USLT(encoding=3, text=meta["unsynchronized_lyrics"])
        )
    tags.add(mutagen.id3.TALB(encoding=3, text=meta["release_title"]))
    tags.add(mutagen.id3.TDRC(encoding=3, text=meta["release_date"]))
    tags.add(mutagen.id3.TDRL(encoding=3, text=meta["release_date"]))
    if meta["genre"]:
        tags.add(mutagen.id3.TCON(encoding=3, text=meta["genre"]))
    tags.add(mutagen.id3.TPUB(encoding=3, text=meta["labels"]))
    if meta.get("track_number"):
        if meta.get("tracks_total"):
            tags.add(
                mutagen.id3.TRCK(
                    encoding=1,
                    text="{}/{}".format(
                        meta["track_number"], meta["tracks_total"]
                    ),
                )
            )
        else:
            tags.add(
                mutagen.id3.TRCK(encoding=1, text=str(meta["track_number"]))
            )
    if meta.get("volume_number"):
        tags.add(
            mutagen.id3.TPOS(
                encoding=3,
                text="{}/{}".format(
                    meta["volume_number"], meta["volumes_total"]
                ),
            )
        )
    tags.add(
        mutagen.id3.TXXX(
            encoding=3, desc="audio_source", text=meta["audio_source"]
        )
    )
    tags.add(
        mutagen.id3.TXXX(
            encoding=3,
            desc="yandex_music_track_id",
            text=meta["yandex_music_track_id"],
        )
    )
    tags.add(
        mutagen.id3.TXXX(
            encoding=3,
            desc="{}_imported".format(user_tag_prefix),
            text=meta["{}_imported".format(user_tag_prefix)],
        )
    )

    # save ID3 to content file
    tags.save(track_path)


def save_audio(track, track_path, type="mp3", bitrate=320):
    track_path = track_path.with_suffix("." + type)
    if not is_saved(track_path):
        try:
            track.download(track_path, type, bitrate)
        except yandex_music.exceptions.InvalidBitrateError:
            track.download(track_path, type)


def complete_with_nines(time_string: str) -> str:
    pattern = "9999-99-99T99:99:99"
    return time_string + pattern[len(time_string) :]


def earliest_time_string(time_strings: list) -> str:
    return sorted(time_strings, key=complete_with_nines)[0]


def get_album_meta(albums, track=None):
    album_metas = []
    for album in albums:
        release = {
            "genre": album.genre,
            "labels": [l.name for l in album.labels],
        }

        title = trim_original_mix(album.title)
        if album.version:
            title += " ({})".format(album.version)
        release["release_title"] = trim_original_mix(title)

        if album.start_date:
            print("Start date:", album.start_date)
        dates = ["9999"]
        if album.release_date:
            if album.release_date[:19].endswith("T00:00:00"):
                dates.append(album.release_date[:10])
            else:
                dates.append(album.release_date[:19])
        if album.year:
            dates.append(str(album.year))
        if album.original_release_year:
            dates.original_release_year(str(album.year))
        release_date = earliest_time_string(dates)
        release["release_date"] = earliest_time_string(dates)

        if album.track_position:
            release["track_number"] = album.track_position.index
        volumes = album.with_tracks().volumes
        if volumes and len(volumes) > 1:
            if track:
                for volume in volumes:
                    for item in volume:
                        if item.id == track.id:
                            release["tracks_total"] = len(volume)
                            break
                    if release.get("tracks_total"):
                        break
            release["volume_number"] = album.track_position.volume
            release["volumes_total"] = len(volumes)
        else:
            release["tracks_total"] = album.track_count

        album_metas.append(release)

    album_metas.sort(key=lambda x: complete_with_nines(x["release_date"]))
    return album_metas[0]


def get_track_meta(track):
    meta = {
        "title": trim_original_mix(track.title),
        "version": track.version,
        "publisher": track.major.name,
        "yandex_music_track_id": track.id,
        "language": None,
        "unsynchronized_lyrics": None,
    }

    supplement = track.get_supplement()
    if supplement.lyrics:
        meta["language"] = supplement.lyrics.text_language
        meta["unsynchronized_lyrics"] = supplement.lyrics.lyrics

    if meta["version"]:
        meta["version"] = trim_original_mix(meta["version"])
    meta["artists"] = []
    for name in track.artists_name():
        if not meta["version"] or name not in meta["version"]:
            meta["artists"].append(name)

    if meta["version"]:
        meta["title_combined"] = "{} ({})".format(
            meta["title"], meta["version"]
        )
    else:
        meta["title_combined"] = meta["title"]

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

    imported_tag_name = "{}_imported".format(user_tag_prefix)
    meta[imported_tag_name] = playlist_record.timestamp[:19]
    meta["audio_source"] = "Yandex Music"
    print(meta)

    # save audio stream to content file
    file_name = convert_to_file_name(
        "{} - {} ({})".format(
            ", ".join(meta["artists"]),
            meta["title_combined"],
            meta["yandex_music_track_id"],
        )
    )
    track_path = user_save_path / file_name

    # save_yandex_track_meta(track_path, track)
    save_audio(track, track_path)
    update_id3(track_path, meta, user_tag_prefix)
    update_id3_artwork(track_path, track)

    # verify if file is saved
    if not is_saved(user_save_path / (file_name + ".mp3")):
        raise


def load_saved_ids(path_to_saved_ids: pathlib.Path) -> list:
    """Return a list of saved IDs from file"""
    if path_to_saved_ids.is_file():
        return path_to_saved_ids.read_text(encoding="utf-8").split("\n")
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
    for track_short in yandex_music_client.users_likes_tracks():
        if track_short.id not in saved_ids:
            print(
                "https://music.yandex.ru/album/{}/track/{}".format(
                    track_short.album_id, track_short.id
                )
            )
            try:
                save_track(
                    track_short,
                    user_tag_prefix,
                    user_save_path,
                )
            except yandex_music.exceptions.NetworkError as e:
                print(e)
                time.sleep(60)
            with path_to_saved_ids.open("a+") as file:
                file.write(track_short.id + "\n")


def get_download_path(nested_path: str) -> pathlib.Path:
    """Return the default downloads path for Linux or Windows"""
    if os.name == "nt":
        import winreg

        sub_key = (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer"
            "\Shell Folders"
        )
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            downloads = pathlib.Path(
                winreg.QueryValueEx(key, downloads_guid)[0]
            )
    else:
        downloads = pathlib.Path.home().joinpath("Downloads")
    return downloads.joinpath(nested_path)


def reserve(music_path):
    user_tag_prefix = "sweetall"
    print("User tag prefix:", user_tag_prefix + "_*")

    user_save_subdir = "!!Imported"
    # user_save_path = get_download_path(user_save_subdir)
    user_save_path = pathlib.Path(music_path).joinpath(user_save_subdir)
    print("Download to:", user_save_path)

    user_token = "AQAAAAABXPQDAAG8XnMPg_r6L0JCtc_Ehhrs-hA"
    yandex_music_client = yandex_music.Client(user_token).init()

    save_favorite_tracks(
        yandex_music_client,
        user_save_path,
        user_save_path / "_saved_from_yandex_music.txt",
        user_tag_prefix,
    )


def win_timedtsmp_to_time_string(timestamp):
    value = datetime.datetime(1601, 1, 1) + datetime.timedelta(
        seconds=int(timestamp) / 10000000
    )
    return value.isoformat()  # strftime('%Y-%m-%dT%H:%M:%S.%f')


def normalize_time_string(ts):
    ts = ts.strip()
    ts = ts.removesuffix(".000000").removesuffix(".000")
    ts = ts.removesuffix("00:00:00").removesuffix("T")
    ts = ts.removesuffix("-00").removesuffix("-00")
    if ts == "0000":
        return "9999"
    return ts


def merge_mp3_tags_to_imported(
    track_path, user_tag_prefix, update_id3_version=False
):
    if track_path.suffix != ".mp3":
        return None
    print("\n    ", track_path)
    tags = mutagen.id3.ID3()
    try:
        tags.load(track_path, translate=False)
    except mutagen.id3._util.ID3NoHeaderError:
        print("File have no ID# tags")
    tag_version = tags.version[1]

    target_tag_name = "{}_imported".format(user_tag_prefix)
    current_imported = tags.get("TXXX:{}".format(target_tag_name))

    # remove string time values
    tags_to_remove = {
        target_tag_name,
        "ACCESSED",
        "added",
        "created",
        "CREATION_TIME",
        "imported",
        "imported_win_created",
        "MODIFIED",
    }
    tag_names = set(s for s in tags_to_remove)
    tag_names = tag_names.union(set(s.lower() for s in tags_to_remove))
    tag_names = tag_names.union(set(s.upper() for s in tags_to_remove))
    tag_names = tag_names.union(set(s.title() for s in tags_to_remove))
    tag_names = tag_names.union(set(s.capitalize() for s in tags_to_remove))

    dates = []
    for name in tag_names:
        id3_name = "TXXX:{}".format(name)
        if tags.get(id3_name):
            d = str(tags.pop(id3_name))
            print(id3_name, d, " -> ", normalize_time_string(d))
            dates.append(normalize_time_string(d))

    # remove Windows timestamps
    tags_to_remove = ["ADDED_TIMESTAMP"]
    tag_names = set(s for s in tags_to_remove)
    tag_names = tag_names.union(set(s.lower() for s in tags_to_remove))
    tag_names = tag_names.union(set(s.upper() for s in tags_to_remove))
    tag_names = tag_names.union(set(s.title() for s in tags_to_remove))
    tag_names = tag_names.union(set(s.capitalize() for s in tags_to_remove))

    for name in tag_names:
        id3_name = "TXXX:{}".format(name)
        if tags.get(id3_name):
            ts = str(tags.pop(id3_name))
            d = win_timedtsmp_to_time_string(ts)
            print(id3_name, d)
            dates.append(d)

    # remove Unix timestamps
    tags_to_remove = ["imported_win_created_unix_ts"]
    tag_names = set(s for s in tags_to_remove)
    tag_names = tag_names.union(set(s.lower() for s in tags_to_remove))
    tag_names = tag_names.union(set(s.upper() for s in tags_to_remove))
    tag_names = tag_names.union(set(s.title() for s in tags_to_remove))
    tag_names = tag_names.union(set(s.capitalize() for s in tags_to_remove))

    for name in tag_names:
        id3_name = "TXXX:{}".format(name)
        if tags.get(id3_name):
            ts = str(tags.pop(id3_name))
            d = datetime.datetime.fromtimestamp(float(ts)).isoformat()
            print(id3_name, d)
            dates.append(d)

    dates.append(
        datetime.datetime.fromtimestamp(
            float(track_path.stat().st_ctime)
        ).isoformat()
    )
    dates.append(
        datetime.datetime.fromtimestamp(
            float(track_path.stat().st_mtime)
        ).isoformat()
    )

    print(dates)
    new_imported = earliest_time_string(dates)
    print(current_imported, " -> ", new_imported)

    if current_imported != new_imported or len(dates) != 3:
        print("Need to update sweetall_imported.")
        if tags.version[1] < 3:
            tags.update_to_v24()
            tag_version = 4
        tags.add(
            mutagen.id3.TXXX(
                encoding=3,
                desc=target_tag_name,
                text=new_imported,
            )
        )

        # save ID3 to content file
        print("ID3V2 version:", tags.version[1])
        tags.save(track_path, v2_version=tag_version)
        print("-" * 80)
        print()


def update_tag_imported(p):
    for nested_path in pathlib.Path(p).iterdir():
        if nested_path.is_dir():
            update_tag_imported(nested_path)
        elif nested_path.suffix == ".mp3":
            merge_mp3_tags_to_imported(nested_path, "sweetall")


if __name__ == "__main__":
    music_path = r"E:\YandexDisk\music"
    reserve(music_path)

    music = [
        r"E:\downloads",
        r"E:\YandexDisk\DJ Full Tracks",
        r"E:\YandexDisk\DJ Tool Tracks",
        r"E:\YandexDisk\mixtapes",
        r"E:\YandexDisk\music",
    ]


"""
    TODO:

- Update_tag_imported for FLAC, Vorbis, iTunes M4A, WMA, Opus

- detect distinct tracks by expression:
  track_string_id = ' '.join([title, version, artists])
  track_string_id.translate({ord(i): None for i in '.,:'})
                 .leave only lower letter + numbers sep by spaces

- create SQLite Table and link track_string_id, yandex_id, shazam_id

2. Get a sound from every track and fingerpint it
   https://github.com/jiaaro/pydub



"""
