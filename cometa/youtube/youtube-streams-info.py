import pyperclip
import pytube

def show_progress_bar(stream, chunk, file_handle, bytes_remaining):
    print(f'  MBytes remaining: {bytes_remaining/1000000}         ', end='\r')
    #Stream : {stream}, chunk : {chunk}, file_handle : {file_handle},

url = pyperclip.paste()
video_id = pytube.extract.video_id(url)
video = pytube.YouTube(url)
title = video.title
video.register_on_progress_callback(show_progress_bar)
streams = video.streams.all()

for i in streams:
    print(i)


#vstream.download(output_path='C:/Users/okean/Music', filename=f'{video_id} {title} V')
#astream.download(output_path='C:/Users/okean/Video', filename=f'{video_id} {title} A')
