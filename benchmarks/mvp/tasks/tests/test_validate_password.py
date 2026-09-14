import importlib.util
from pathlib import Path


def _module():
    path = Path(__file__).with_name("generated_tests.py")
    spec = importlib.util.spec_from_file_location("generated_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_tests_cover_valid_and_invalid_passwords():
    module = _module()
    module.test_valid_password()
    module.test_rejects_each_requirement()
