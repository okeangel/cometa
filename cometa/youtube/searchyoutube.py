import urllib.request
import json
import time


def rm_words_from_file(string, rep, filename):
    """
    replace unwanted substrings by spaces to save the separation
    """
    with open(filename) as file:
        for word in file.read().splitlines():
            string = string.replace(word, rep)
    return string


def check(string, keywords):
    string = string.lower()
    for word in keywords:
        if word not in string:
            return False
    return True


def search(inp):
    query = inp.lower()

    # replace garbage substrings like "feat." by spaces to save the separation
    query = rm_words_from_file(query, ' ', 'search-conf-words-deleting.txt')
    query = rm_words_from_file(query, ' ', 'search-conf-words-replacing.txt')

    keywords = query.split()
    query = '+'.join(keywords)
    print(f'Searching query is: \"{query}\"')
    # %7C is "pipeline" symbol ("or"), also can use "-" sign
    # urllib.quote(s.decode('ascii').encode('cp1251'))
    # urllib.request.quote(query.decode('ascii').encode('cp1251'))
    query = urllib.parse.quote(query)

    # combine basic query url
    with open('search-conf-api-key.txt') as file:
        api_key = file.read()
    parameters = f'key={api_key}&part=snippet&maxResults=50&q={query}&regionCode=US&safeSearch=none&order=relevance' \
                 f'&type=video'
    api_url = 'https://www.googleapis.com/youtube/v3/search?'
    first_url = api_url + parameters
    next_page_url = first_url

    ''' Get, clear & compare results.
    If we have at least 1 more, we repeat iteration 1 more time. '''

    # initialize the cycling
    n = 0
    items = []
    checked = []
    reply = {}

    while True:
        n += 1

        # get a responce
        print(next_page_url)
        resp = urllib.request.urlopen(next_page_url)
        #        try:
        #            resp = urllib.request.urlopen(next_page_url)
        #        except:
        #            print('Response error. Check Internet connection and API key.')
        #            break
        resp_dict = json.load(resp)
        items = items + resp_dict['items']
        totalResults = resp_dict['pageInfo']['totalResults']
        # its a list of results, each item is a dictionary
        print(f'Iteration {n}. Received {len(items)} of {totalResults} total results.')

        # remove titles without some keywords
        for item in items:
            title = item['snippet']['title']
            if check(item['snippet']['title'], keywords):
                checked.append(item)
        print(f'List reduced from {len(items)} to {len(checked)}.')
        items.clear()
        if not checked:
            print('No new checked results. Breaking.')
            break

        # publishedBefore=1970-01-01T00:00:00Z RFC 3339 formatted date-time
        times = []
        for item in checked:
            print(item['snippet']['publishedAt'])
            item['snippet']['publishedAt'] = time.strptime(item['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%S.%fZ')
            # times.append(item['snippet']['publishedAt'])

        if reply:
            checked.append(reply)

        for i in range(len(checked) - 1):
            if checked[0]['snippet']['publishedAt'] < checked[1]['snippet']['publishedAt']:
                del checked[1]
            else:
                del checked[0]

        reply = checked.pop()
        print('Checked state: ' + str(checked))
        print('Best date: ' + str(time.strftime("%Y-%m-%d", reply['snippet']['publishedAt'])))

        try:
            next_page_url = first_url + '&pageToken={}'.format(resp_dict['nextPageToken'])
        except:
            print(resp['nextPageToken'])
            break

    if reply:
        title = reply['snippet']['title']
        date = time.strftime("%Y-%m-%d", reply['snippet']['publishedAt'])
        channel = reply['snippet']['channelTitle']
        video_id = reply['id']['videoId']

        print(
            f'\"{title}\"\npublished at: - > {date} < -\non channel \"{channel}\".\n'
            f'(https://www.youtube.com/watch?v={video_id})') 

        result_meta = {'inp': inp, 'title': title, 'date': date, 'channel': channel, 'video_id': video_id}
        return result_meta
