import pyperclip
import searchyoutube

while True:

    inp = input('Insert track name or Ctrl+C and Enter to search, or "x" to exit: ')
    if inp == 'x':
        break
    if inp == '':
        inp = pyperclip.paste()
    result_meta_youtube = searchyoutube.search(inp)
    print('Result: ' + str(result_meta_youtube))
    if result_meta_youtube:
        pyperclip.copy(result_meta_youtube['date'])
