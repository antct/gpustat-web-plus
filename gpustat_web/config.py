import configparser
import os
import threading

def config_lock(func):
    def wrapper(*arg, **kwargs):
        with config_parser._instance_lock:
            return func(*arg, **kwargs)
    return wrapper

class config_parser():
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(config_parser, "_instance"):
            with config_parser._instance_lock:
                if not hasattr(config_parser, "_instance"):
                    config_parser._instance = object.__new__(cls)
        return config_parser._instance

    def __init__(self, file_path):
        # self._base_path = os.path.dirname(__file__)
        self._config_file = file_path
        self._data = configparser.ConfigParser()
        # self._data = configparser.RawConfigParser()
        self._data.read(self._config_file)

    @config_lock
    def get(self, section, key):
        return self._data.get(section, key)