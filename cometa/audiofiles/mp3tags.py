import os
import glob
import tinytag
from win32com.shell import shell, shellcon


def deltorecyclebin(filename):
    if not os.path.exists(filename):
        return True
    res = shell.SHFileOperation((0, shellcon.FO_DELETE, filename, None, shellcon.FOF_SILENT | shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION, None, None))
    if not res[1]:
        os.system('del ' + filename)


def scan(folder):
    music_exts = (".mp3", ".wav", ".aiff", ".m4a", ".flac", ".ogg", ".mka", ".dts", ".wma")
    arts = ["cover", "artwork", "scan", "booklet", "облож", "\\art"]
    n = 0
    for root, dirs, names in os.walk(folder):
        if names:
            no_music = True
            for name in names:
                if name.endswith(music_exts):
                    # try:
                    #    temp_track = tinytag.TinyTag.get(root + '\\' + name)
                    #    print(n, temp_track.artist, "-", temp_track.title)
                    # except Exception as e:
                    no_music = False
                    break

            if no_music:
                if any(art in root.lower() for art in arts):
                    # print("Cover dir", root)
                    continue
                if not dirs:
                    print("No Music in", root)


        else:
            if not dirs:
                print("Empty", root)
                deltorecyclebin(root)


def lower_exts(target_folders):
    for folder in target_folders:
        files = []
        for root, dirs, names in os.walk(folder):
            for n in names:
                files.append([root, n])

        for fname in files:
            name, ext = os.path.splitext(fname[1])
            ext_lower = ext.lower()
            if ext != ext_lower:
                oldname = os.path.join(fname[0], fname[1])
                newname = os.path.join(fname[0], name + ext_lower)
                print(oldname)
                os.rename(os.path.join(oldname), os.path.join(newname))


def collect_exts(target_folders):
    exts = set()
    for folder in target_folders:

        files = []
        for root, dirs, names in os.walk(folder):
            for name in names:
                files.append([root, name])

        for f in files:
            name, ext = os.path.splitext(f[1])
            exts.add(ext)

    return exts


if __name__ == '__main__':

    music_folders = [
        r"E:\YandexDisk\DJ",
        r"E:\YandexDisk\TraktorStem",
        r"E:\YandexDisk\DJ 9 - Music Tracks to Save in Reserve",
        r"E:\music"
    ]

    test_folders = [r"F:\DJ"]

    for f in music_folders:
        scan(f)
"""
    fls = [r"D:", r"E:\books", r"F:"]
    total = collect_exts(fls)
    total = list(total)
    total.sort()
    print(total)
    with open('exts.txt', 'w+', encoding="utf-8") as file:
        file.write('\n'.join(total))
"""