from dataclasses import asdict


class ModelBase:
    def dump(self):
        return asdict(self)
