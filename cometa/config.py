import configparser
import pathlib


def get_data_paths() -> tuple:
    """Return roaming and local user data paths"""
    portable_path = pathlib.Path("portable")
    if portable_path.is_dir():
        return (
            portable_path.joinpath("user"),
            portable_path.joinpath("host", "local"),
        )
    return (
        pathlib.Path.home().joinpath(".cometa"),
        pathlib.Path.home().joinpath(".cometa", ".local"),
    )


def get_config(userdata_path):
    config = configparser.ConfigParser()
    config_dir = userdata_path / "config"
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
    config_path = config_dir / "main.ini"
    if not config_path.is_file():
        print(
            """
Enter the paths to the directories that contain the music. First, input path
line, then press Enter, then input the next path line, Enter, and so on.
In the end just press Enter again, with no symbols.
""".strip()
        )
        music_dirs = []
        while True:
            text = input()
            if not text:
                break
            music_dir = pathlib.Path(text)
            if not music_dir.is_dir():
                print("Folder not found at this path. Please input again.")
                continue
            music_dirs(music_dir)

        print("From what date should the data be saved?")
        print("(for example 2017-07-14 - since the launch of Binance)")
        music_data_dir = datetime.date.fromisoformat(input())
        save_config(userdata_path, music_dirs, music_data_dir)
    else:
        config.read(config_path)
        music_data_dir = pathlib.Path(
            config["MUSIC COLLECTION"].pop("music_data_dir")
        )

        music_dirs = []
        for key in config["MUSIC COLLECTION"].keys():
            if key.startswith("music_dir_"):
                music_dirs.append(
                    pathlib.Path(config["MUSIC COLLECTION"].pop(key))
                )
    return music_dirs, music_data_dir


def save_config(userdata_path, music_dirs, music_data_dir):
    config = configparser.ConfigParser()
    config["MUSIC COLLECTION"] = {
        "music_data_dir": str(music_data_dir),
    }

    music_dirs = {f"music_dir_{i}": str(d) for i, d in enumerate(music_dirs)}
    config["MUSIC COLLECTION"].update(music_dirs)

    config_path = userdata_path / "config" / "main.ini"
    with open(config_path, "w") as configfile:
        config.write(configfile)


userdata_path, localdata_path = get_data_paths()
music_dirs, music_data_dir = get_config(userdata_path)
