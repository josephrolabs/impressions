import pytest
from solution import solve
def test_order(): assert solve(['a','b','c'], [('a','c'),('b','c')]) == ['a','b','c']
def test_empty(): assert solve([], []) == []
def test_cycle():
    with pytest.raises(ValueError): solve(['a','b'], [('a','b'),('b','a')])
