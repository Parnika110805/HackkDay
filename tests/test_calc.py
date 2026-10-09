import pytest
from app.nutrition.calc import (
    pack_total,
    per_serving_from_100g,
    per_100g_from_serving,
    sugar_in_teaspoons,
    sodium_mg_to_salt_g,
    compare_two
)

def test_pack_total():
    assert pack_total(4.5, 4) == 18.0
    assert pack_total(None, 4) is None
    assert pack_total(10, None) is None

def test_per_serving_from_100g():
    # 18g sugar per 100g, 25g serving -> 4.5g
    assert per_serving_from_100g(18.0, 25) == 4.5
    assert per_serving_from_100g(None, 25) is None

def test_per_100g_from_serving():
    assert per_100g_from_serving(4.5, 25) == 18.0
    assert per_100g_from_serving(5.0, 0) is None

def test_sugar_in_teaspoons():
    assert sugar_in_teaspoons(18.0) == 4.5
    assert sugar_in_teaspoons(4.0) == 1.0
    assert sugar_in_teaspoons(None) is None

def test_sodium_mg_to_salt_g():
    # 400 mg sodium -> 1.0 g salt
    assert sodium_mg_to_salt_g(400) == 1.0
    assert sodium_mg_to_salt_g(380) == 0.95
    assert sodium_mg_to_salt_g(None) is None

def test_compare_two():
    label_a = {"per_100g": {"sugar_g": 10.0, "protein_g": 5.0}}
    label_b = {"per_100g": {"sugar_g": 15.0, "protein_g": 5.0}}
    res = compare_two(label_a, label_b)
    assert res["sugar_g"]["diff_pct"] == 50.0
    assert res["protein_g"]["diff_pct"] == 0.0
