import pytest
from solution import solve
def test_aggregate(): assert solve([('a',2),('a',3),('b',1)]) == {'a':5,'b':1}
def test_sorted(): assert list(solve([('z',1),('a',1)])) == ['a','z']
def test_negative():
    with pytest.raises(ValueError): solve([('a',-1)])
