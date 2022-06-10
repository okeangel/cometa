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
#vstream = video.streams.filter(type='video').order_by('subtype').order_by('resolution').desc().first()
astream = video.streams.filter(audio_codec='opus').order_by('bitrate').desc().first()

#print(vstream)
print(astream)

#vstream.download(output_path='C:/Users/okean/Music', filename=f'{video_id} {title} V')
astream.download(filename=f'{video_id} {title} A')
