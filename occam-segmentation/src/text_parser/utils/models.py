class Text(list[str]):
    """
    A class representing a text as a list of sentences.
    """

    @classmethod
    def from_file(cls, file_path: str) -> "Text":
        raise NotImplementedError

    @classmethod
    def from_bytes(cls, b: bytes) -> "Text":
        raise NotImplementedError

    @classmethod
    def from_string(cls, string: str) -> "Text":
        raise NotImplementedError
