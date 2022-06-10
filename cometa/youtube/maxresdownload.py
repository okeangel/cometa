import urllib.request
import json
import os
import time

def get_video_ids_in_playlist(playlist_id,api_key):
    '''returns list of the video_ids in playlist'''

    base_request_url = 'https://www.googleapis.com/youtube/v3/playlistItems?'
    first_url = base_request_url+f'key={api_key}&part=contentDetails&maxResults=50&playlistId={playlist_id}'
    next_page_url = first_url #next pages urls needs addition &pageToken={next_page_token} but first page not need it
    actual_video_ids = set()
    
    while True:
        try:
            resp = urllib.request.urlopen(next_page_url)
        except:
            print(f'HTTP GET failed for playlist {playlist_id}')
            break
        resp_dict = json.load(resp)

        for i in resp_dict['items']:
            if i['kind'] == "youtube#playlistItem":
                actual_video_ids.add(i['contentDetails']['videoId'])

        try:
            next_page_token = resp_dict['nextPageToken']
            next_page_url = first_url + f'&pageToken={next_page_token}'
        except:
            break
    return actual_video_ids


def increase_status_bar(symbol):
    '''print one more symbol without new line'''
    print(symbol, end='', flush=True)


print('Maxresdefault Mass Downloader - saving thumbinalis from a playlists.')

total = 0 #quantity of stored images
new = 0 #quantity of new loaded images
errors = 0 #quantity of images not loaded by errors
old_video_ids = set() #list of video_ids which we loaded
actual_video_ids = set() #fresh printed list of actual ids
all_video_ids = set() #combines old and actual
new_video_ids = [] #list of video_ids to load new images
vids_file_name = 'maxresdownload-data-vids.txt' #here storing video IDs which we tried to store thumbinails - for not loading older and removed by user images

print('Preparing list of video...')

with open ('maxresdownload-conf-api-key.txt') as file:
    api_key = file.read()

try:
    with open (vids_file_name) as file:
        for id in file.read().splitlines():
            old_video_ids.add(id)
except FileNotFoundError:
    if input('File with previous loaded videoIDs not found.\nDo we need continue load from scratch?\nType "n" if "No", or skip if continue : ').lower() == 'n':
        raise

with open('maxresdownload-conf-playlists-id.txt') as file:
    for playlist_id in file.read().splitlines():
        actual_video_ids.update(get_video_ids_in_playlist(playlist_id,api_key))

with open ('maxresdownload-conf-target-dir.txt') as file:
    dir_path = file.read()

# if I will need to separate images by playlistId, I will use this
#if not os.path.exists(dir_path):
#    os.mkdir(dir_path)
#    print(f'New directory created: {dir_path}')

# need to reduce
print('Storing list of video ID in a file...')

new_video_ids = actual_video_ids - old_video_ids

total = len(old_video_ids)+len(new_video_ids)

with open (vids_file_name, 'a+') as file:
    for id in new_video_ids:
        file.write(f'{id}\n')


print('Search\'n\'load new files...')
for id in new_video_ids:
    file_path=f'{dir_path}\{id}.jpg'
    if not os.path.exists(file_path):
        maxresdefault_url = f'https://img.youtube.com/vi/{id}/maxresdefault.jpg'
        try:
            image = urllib.request.urlopen(maxresdefault_url).read()
        except:
            errors+= 1
            increase_status_bar('X')
            continue
        file = open(file_path,'wb')
        file.write(image)
        file.close()
        new+= 1
        increase_status_bar('+')

print(f'\nWe have {errors} not loaded and {new} new files. Total {total} download records, Sir!')
time.sleep(10)
