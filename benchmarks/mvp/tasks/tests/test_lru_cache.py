from solution import LRUCache
def test_missing(): assert LRUCache(1).get('x') == -1
def test_evict():
    c=LRUCache(1); c.put('a',1); c.put('b',2); assert c.get('a') == -1
def test_refresh():
    c=LRUCache(2); c.put('a',1); c.put('b',2); c.get('a'); c.put('c',3); assert c.get('b') == -1
