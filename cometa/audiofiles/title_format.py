import datetime


def title_format(title):
    pass


def windows_filetime(timestamp):
    return datetime.datetime(1601, 1, 1)\
           + datetime.timedelta(seconds=timestamp/10000000)
