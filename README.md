
Cometa
======

Artwork organizer. Store your notes, ratings, tags, other meta, linked to the artwork ID (and title). Cometa links ID to text, notation, images, audio and video stored locally or published on web. Cometa backing up media from web.



Setup
-----



Usage
-----



Основные идеи
-------------

# Рейтинг артистов

Важнее не известность артиста, а "импакт" - то, насколько высоко ставят его люди, знакомые с большим количеством разных треков.

Рейтинг артиста = оценка * вес оценщика (кол-во подтверждённых разных артистов, которых слушал)


# Добавление обложки в файл со звуком

1. Выбираем файл (JPEG, PNG, TIFF)
2. Вручную выделяем кроп-область 1:1 или Custom, автообрезаем.
3. Автоуменьшаем под точный размер или на целую величину, чтобы попасть в
промежуток между min и max шириной и высотой.
4. Сохраняем в jpeg в тэге.


# Резервирование коллекции

Периодически:

- подключиться к Yandex Music
- получить шорт-треки из плейлистов
- если есть track_id, которых нет в базе:
	- скачать мету, аудио и обложку
    - объединить их в файл
	- добавить в мету файла:
	  - replay gain
	  - hash of audio stream (чтобы быстро обнаруживать точные совпадения)
	  - fingerprint (отслеживать похоие треки)
	- добавить мету в базу данных (а стрим - можно и в файлы)


# Отбор аудиодорожки лучшего качества

- Сравнить аудио.
  - Если есть похожий - добавить к нему в группу.
  - Если похожих нет - создать новую группу.
- Показать все группы, в которых  больше одного трека, пользователю. Сортировать по выигрышу места = сумма размеров файлов - размер крупнейшего файла.
  - Внутри каждой группы сортировать по: длина, битрейт.
  - Все тэги внутри группы - объединяются в один набор мета-данных. Пользователь может отменить объединение (чтобы объединить руками) или подтвердить - тогда все файлы получат этот тэг.
  - Пользователь выбирает один трек, который остаётся - Комета удаляет остальные треки, и удаляет группу из памяти, переходит к следующей группе.



Источники вдохновения
---------------------

## fingerprint

https://shivama205.medium.com/audio-signals-comparison-23e431ed2207
https://github.com/kdave/audio-compare