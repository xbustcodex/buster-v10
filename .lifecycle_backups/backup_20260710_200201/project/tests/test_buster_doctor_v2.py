import importlib.util
import sys
from pathlib import Path


def load_doctor_module():
    path = Path("scripts/buster_doctor.py")
    spec = importlib.util.spec_from_file_location("buster_doctor", path)
    module = importlib.util.module_from_spec(spec)

    sys.modules[spec.name] = module

    spec.loader.exec_module(module)
    return module


def test_check_result_flags():
    module = load_doctor_module()
    ok = module.CheckResult("x", "OK", "")
    warn = module.CheckResult("x", "WARN", "")
    fail = module.CheckResult("x", "FAIL", "")

    assert ok.ok
    assert warn.warn
    assert fail.fail


def test_doctor_add_records_result():
    module = load_doctor_module()
    doctor = module.BusterDoctor(run_tests=False)
    doctor.add("Test", "OK", "works")

    assert len(doctor.results) == 1
    assert doctor.results[0].name == "Test"
    assert doctor.exit_code() == 0


def test_doctor_exit_code_fails_on_failure():
    module = load_doctor_module()
    doctor = module.BusterDoctor(run_tests=False)
    doctor.add("Bad", "FAIL", "broken")

    assert doctor.exit_code() == 1