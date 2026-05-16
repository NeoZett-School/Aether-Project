class Integer:
    def __init__(self, value: int):
        self._value = value
    @property
    def value(self):
        return self._value