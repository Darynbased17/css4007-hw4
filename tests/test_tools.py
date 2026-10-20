import json
import pytest
from tools import calculate, lookup

def test_calculate_normal_math():
    res_str = calculate("48317 * 1.0947")
    res_json = json.loads(res_str)
    assert "result" in res_json
    # Исправленное значение математики
    assert "52892.6199" in res_json["result"]

def test_calculate_refuses_import():
    res_str = calculate("__import__('os').system('echo hi')")
    res_json = json.loads(res_str)
    assert "error" in res_json

def test_calculate_refuses_class_attribute():
    res_str = calculate("(1).__class__")
    res_json = json.loads(res_str)
    assert "error" in res_json

def test_calculate_refuses_huge_exponent():
    res_str = calculate("9**9**9")
    res_json = json.loads(res_str)
    assert "error" in res_json

def test_calculate_division_by_zero():
    res_str = calculate("10 / 0")
    res_json = json.loads(res_str)
    assert "error" in res_json

def test_lookup_correct_2025_number():
    res_str = lookup("Brightwater", "population")
    res_json = json.loads(res_str)
    assert "result" in res_json
    assert "44,675" in res_json["result"]

def test_lookup_misspelled_name():
    res_str = lookup("Ossbrige", "population")
    res_json = json.loads(res_str)
    assert "error" in res_json
    assert "Ossbridge" in res_json["error"]
    assert "Ossford" in res_json["error"]

def test_lookup_similar_names_do_not_mix():
    res_str1 = lookup("Ossbridge", "area")
    res_json1 = json.loads(res_str1)
    assert "1,284.6" in res_json1.get("result", "")
    
    res_str2 = lookup("Ossford", "area")
    res_json2 = json.loads(res_str2)
    assert "846.2" in res_json2.get("result", "")
    assert "1,284.6" not in res_json2.get("result", "")

def test_lookup_ignores_archived_profile():
    res_str = lookup("Tarnvale", "population")
    res_json = json.loads(res_str)
    assert "result" in res_json
    assert "65,030" not in res_json["result"]
    assert "71,388" in res_json["result"]

def test_lookup_region_tariff():
    res_str = lookup("Region", "tariff")
    res_json = json.loads(res_str)
    assert "result" in res_json
    assert "142.35" in res_json["result"]