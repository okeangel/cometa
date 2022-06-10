def parse_virtualdj_playlists(filename):
    with open(filename, encoding="ansi") as file:
        lines = file.readlines()

    collection = dict()
    date = '0000-00-00'
    while lines:
        line = lines.pop(0)
        if "VirtualDJ History - " in line:
            date = "-".join([line[20:24], line[25:27], line[28:30]])
            collection.setdefault(date, [])
        if line != "\n":
            collection[date].append(line)

    sorted_dict = dict(sorted(collection.items(), key=lambda x: x[0].lower()))

    with open("E:\\MixTapes SA Production\\tracklist-bis.txt", "w") as file:
        for v in sorted_dict.values():
            for k in v:
                file.write(k)
            file.write('\n')


if __name__ == "__main__":
    parse_virtualdj_playlists("E:\\MixTapes SA Production\\tracklist2.txt")
