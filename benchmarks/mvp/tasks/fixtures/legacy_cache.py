class LegacyCache:
    """Existing insertion-ordered cache that never refreshes reads or evicts."""

    def __init__(self):
        self.data = {}

    def read(self, key):
        return self.data.get(key, -1)

    def write(self, key, value):
        self.data[key] = value
