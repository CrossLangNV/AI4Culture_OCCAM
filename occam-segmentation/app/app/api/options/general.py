class Option:
    _name: str
    _description: str

    def __init__(self, method=None):
        self._method = method

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    def dict(self):
        return {"name": self.name, "description": self.description}

    def __call__(self, text: list[str]) -> list[str]:
        return self._method(
            text,
        )


class Options:
    _options: list[Option]

    def get_options(self) -> list[dict[str, str]]:
        return [option.dict() for option in self._options]

    def get_option(self, name: str):
        for option in self._options:
            if option.name.lower() == name.lower():
                return option

        raise ValueError(f"Option {name} not found")
