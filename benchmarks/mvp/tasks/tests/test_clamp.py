import pytest
from solution import solve
def test_inside(): assert solve(3, 1, 5) == 3
def test_bounds(): assert solve(-1, 0, 2) == 0 and solve(3, 0, 2) == 2
def test_invalid():
    with pytest.raises(ValueError): solve(1, 2, 1)
