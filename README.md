
Cometa
======

Scans your music directory. Creates audio fingerprints. Looking for duplicated audio.



Setup
-----

Install [Python](https://www.python.org/downloads/), [fpcalc](https://acoustid.org/chromaprint) and [ffmpeg](https://ffmpeg.org/download.html). It is necessary you can call them on the command line by name. [Help for Windows.](https://phoenixnap.com/kb/ffmpeg-windows)

Then download the archive with the project, unpack it into a directory, and type in command line:

    cd parent/path/cometa
    pip install -r requirements.txt


Usage
-----

Type in command line:

    python parent/path/cometa/cometa/cometa.py


How it works
------------

ffmpeg превращает закодированные по-разному файлы в единый простой формат, который способен прочесть fpcalc. fpcalc строит спектрограмму файла, а затем упрощает её до 32 точек по высоте, и 8 точек на 1 секунду по длине. Каждая точка либо заполнена (считаем, что на этой частоте в этот момент времени звук был), либо пуста (считаем, что звука не было). Эта упрощённая карта (двухмерный массив бит) - "отпечаток" (fingerprint).

Cometa получает от fpcalc отпечаток, и сохраняет. Затем сравнивает - похожи ли карты разных треков. Если у обоих отпечатков в соответствующих точках (на нужной секунде и частоте) звук пристутсвует или отстутствует - это 1 балл за то, что треки похожи. Если же в соотвествующих точках в одном отпечатке есть звук, а в другом нету, то это 1 балл за то, что треки различаются. Общее количество баллов - это количество точек, которые мы сравнили, то есь, по сути - это размер отпечатка более короткого трека (или размер того "окна", которое мы выбрали из отпечатков, чтобы сравнивать).

Величина корреляции - это доля совпавших точек из общего числа точек, которые Комета сравнила. Чем больше корреляция отпечатков - тем более похожи сами треки. В среднем корреляция 0.5 - такая будет у большинства треков, и у двух абсолютно случайных шумов. По опыту, 1% самых похожих пар треков имеют корреляцию выше 0.577. Треки с корреляцией выше 0.9 чаще всего являются одной и той же песней, закодированной разными способами, или "клонами", содержащими одинаковую музыку, но опубликованные под разными названиями.



Inspired by
-----------

### fingerprint

- <https://shivama205.medium.com/audio-signals-comparison-23e431ed2207>
- <https://github.com/kdave/audio-compare>
