from dataclasses import asdict, is_dataclass


class ModelBase:
    def dump(self) -> dict:
        if not is_dataclass(self):
            return self.__dict__
        return asdict(self)
