
TODO
====


# fingerprint.py:

- запуск с аргументами:
  - -i --info
  - -s --scan
  - -c --correlate
  - -f --full
  - -p --pair
  - https://habr.com/ru/company/ruvds/blog/440654/
  - https://docs.python.org/3/library/argparse.html

- профили пользователей в ini
- replace legacy calls to 3.11 recommendations (https://github.com/kdave/audio-compare)
- ускорение Numba
- подбор в пул result_chunk определённой длины:
  - перед набором пула узнать, сколько есть свободной памяти (https://stackoverflow.com/questions/11615591/available-and-used-system-memory-in-python)
  - рассчитать, сколько вместится объектов
  - набрать пул с этим количеством объектов
  - выгрузить результаты пула в файл с последовательным номером.
  - (далее эти результаты будут загружаться файл за файлом, и анализироваться так же по очереди)
- проверка, есть ли сохранённые корреляции:
  - сразу при новой итерации, перед созданием чанка, создаём имя чанка. И проверяем, есть ли сохранённый результат с этим чанком? если есть - то переходим к следующей итерации - однако если чанки различны по длине - то как это сделать?

- поиск идей для улучшения фингерпринтов:
  - https://news.ycombinator.com/item?id=8303713
  - https://github.com/topics/audio-fingerprinting?l=python&o=asc&s=stars