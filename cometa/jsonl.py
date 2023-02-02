import pathlib
import json


def dump(lines, path, headline=None):
    path = pathlib.Path(path)
    if path.suffix == '':
        path = path.with_suffix('.jsonl')
    with open(path, 'w', encoding='utf-8') as output_file:
        if headline:
            json.dump(headline,
                      output_file,
                      ensure_ascii=False,
                      separators=(',', ':'))
            output_file.write('\n')
        for line in lines:
            json.dump(line,
                      output_file,
                      ensure_ascii=False,
                      separators=(',', ':'))
            output_file.write('\n')


def load(path):
    path = pathlib.Path(path)
    if path.suffix == '':
        path = path.with_suffix('.jsonl')
    with open(path, encoding='utf-8') as input_file:
        return [json.loads(line) for line in input_file]