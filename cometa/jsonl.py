import pathlib
import json


def fix_suffix(path):
    path = pathlib.Path(path)
    if path.suffix == '':
        path = path.with_suffix('.jsonl')
    return path


def serialize_item(item):
    return json.dumps(item, ensure_ascii=False, separators=(',', ':'))


def dump(items, path, mode='w'):
    path = fix_suffix(path)
    with open(path, mode, encoding='utf-8') as output_file:
        records = map(
            lambda item: serialize_item(item) + '\n',
            items,
        )
        output_file.writelines(records)


def extend(items, path):
    dump(items, path, mode='a')


def append(item, path):
    path = fix_suffix(path)
    with open(path, 'a', encoding='utf-8') as output_file:
        output_file.write(serialize_item(item) + '\n')


def load(path):
    path = fix_suffix(path)
    with open(path, encoding='utf-8') as input_file:
        return [json.loads(line) for line in input_file]


def items_of(path):
    path = fix_suffix(path)
    with open(path, encoding='utf-8') as input_file:
        for line in input_file:
            yield json.loads(line)