from fixtures.password import is_valid


def test_valid_password():
    assert is_valid("Good1!xx")


def test_rejects_each_requirement():
    assert not is_valid("A1!a")
    assert not is_valid("good1!xx")
    assert not is_valid("GOOD1!XX")
    assert not is_valid("Good!xxx")
    assert not is_valid("Good1xxx")
