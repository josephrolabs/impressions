from fixtures.legacy_cache import LegacyCache


class LRUCache(LegacyCache):
    def __init__(self, capacity):
        super().__init__()
        self.capacity = capacity

    def get(self, key):
        value = self.read(key)
        if value == -1:
            return -1
        self.data.pop(key)
        self.write(key, value)
        return value

    def put(self, key, value):
        self.data.pop(key, None)
        self.write(key, value)
        if len(self.data) > self.capacity:
            self.data.pop(next(iter(self.data)))
