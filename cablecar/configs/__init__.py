import glob
import os.path
import typing

import toml


class Configs:
    def __new__(cls: type["Configs"]) -> "Configs":
        _config_files: typing.List[str] = glob.glob(
            os.path.join(os.path.dirname(__file__), "*.toml")
        )
        for config in _config_files:
            _name: str = os.path.splitext(os.path.basename(config))[0]
            setattr(cls, _name, toml.load(config))
        return cls
