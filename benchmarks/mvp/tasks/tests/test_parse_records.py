import pytest
from solution import solve
def test_parse(): assert solve(['Ada <ada@example.com>']) == [{'name':'Ada','email':'ada@example.com'}]
def test_blank(): assert solve(['', ' Bob <b@x.io> ']) == [{'name':'Bob','email':'b@x.io'}]
def test_invalid():
    with pytest.raises(ValueError): solve(['not a record'])
