import configparser
import pathlib
import sys


APP_NAME = 'Cometa'
APP_VERSION = '0.1.4'
RELEASE_DATE = '2023-02-07'


def get_data_paths() -> tuple:
    """Return roaming and local user data paths"""
    portable_path = pathlib.Path('portable')
    if portable_path.is_dir():
        return (
            portable_path.joinpath('user'),
            portable_path.joinpath('host', 'local'),
        )
    return (
        pathlib.Path.home().joinpath('.cometa'),
        pathlib.Path.home().joinpath('.cometa', '.local'),
    )


def get_profile_from_input():
    print(
        """
Enter the paths to the directories that contain the music. First, input path
line, then press Enter, then input the next path line, Enter, and so on.
In the end just press Enter again, with no symbols.
""".strip()
    )
    music_dirs = []
    while True:
        text = input('μ: ')
        if not text:
            break
        music_dir = pathlib.Path(text)
        if not music_dir.is_dir():
            print('Folder not found at this path. Please input again.')
            continue
        music_dirs.append(music_dir)

    print('In which folder to save track data?')
    while True:
        music_data_dir = pathlib.Path(input('>>> '))
        if music_data_dir.is_dir():
            break
        print('Folder not found at this path. Please input again.')
    return music_dirs, music_data_dir


def get_profile_from_config(config_path, collection_name):
    config = configparser.ConfigParser()
    config.read(config_path)
    music_data_dir = pathlib.Path(
        config[collection_name].pop('music_data_dir')
    )

    music_dirs = []
    for key in config[collection_name].keys():
        if key.startswith('music_dir_'):
            music_dirs.append(
                pathlib.Path(config[collection_name].pop(key))
            )
    return music_dirs, music_data_dir


def get_config_dir():
    return get_data_paths()[0] / 'config'


def get_config():
    config_dir = get_config_dir()
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
    config_path = config_dir / 'main.ini'

    if not config_path.exists():
        print('Here is no saved configuration. Let us create an actual one.')
        print('Enter the name of your music collection')
        print('(or your favorite username, nickname or full name).')
        collection_name = input('μ: ')
        music_dirs, music_data_dir = get_profile_from_input()
        update_config(config_path, collection_name, music_dirs, music_data_dir)
    else:
        config = configparser.ConfigParser()
        config.read(config_path)
        collection_names = config.sections()
        displayed_collection_names = [f'"{name}"' for name in collection_names]
        print(f'Known collections: {", ".join(displayed_collection_names)}.')
        print('Input the name of the collection to be processed. If you want\n'
              'to create a new profile, enter new name.'
              ' Or type Enter to exit.')
        collection_name = input('μ: ')
        if collection_name == '':
            print('No name typed. Bye!')
            sys.exit()
        elif collection_name not in collection_names:
            print('This name is a new one. Do you want to describe '
                  'a new collection (Y/n)?')
            decision_new = input('μ: ')
            while True:
                if decision_new.lower() in ['y', 'yes']:
                    music_dirs, music_data_dir = get_profile_from_input()
                    update_config(config_path,
                                  collection_name,
                                  music_dirs,
                                  music_data_dir)
                    break
                elif decision_new.lower() in ['n', 'no']:
                    print('Okay, let you decide what exactly do you want '
                          'to do and then start again.')
                    sys.exit()
                print('So yes or no (y/n)?')
                decision_new = input('μ: ')
    return get_profile_from_config(config_path, collection_name)


def update_config(config_path, collection_name, music_dirs, music_data_dir):
    config = configparser.ConfigParser()
    if config_path.exists():
        config.read(config_path)
    config[collection_name] = {'music_data_dir': str(music_data_dir)}
    mdirs = {f'music_dir_{i}': str(d) for i, d in enumerate(music_dirs)}
    config[collection_name].update(mdirs)
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    return config