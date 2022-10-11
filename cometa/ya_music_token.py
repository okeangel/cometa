import re
import subprocess
import os


def fetch_user_token():
    if os.name == 'nt':
        import winreg            
        subkey = r'htmlfile\shell\open\command'
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, subkey) as key:
            dbrowser_path = winreg.QueryValueEx(key, '')[0]
        browser_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    else:
        browser_path = '/opt/google/chrome/chrome'
    print(dbrowser_path)
    print(browser_path)

    url = 'https://oauth.yandex.ru/authorize'
    query = '?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d'
    command = [
        browser_path,
        '--enable-logging=stderr',
        url + query,
        "--v=4",
    ]
    result = subprocess.run(command, capture_output=True)

    pattern = r'https://music.yandex.ru/#access_token=(.*?)&'
    return re.search(pattern, result.stderr.decode('utf-8')).group(1)

fetch_user_token()