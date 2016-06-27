from os.path import split, join
import json


def load_config():
    file_path = split(split(split(__file__)[0])[0])[0]
    file_path = join(file_path, 'config.json')
    with open(file_path, 'r') as fp:
        return json.load(fp)
