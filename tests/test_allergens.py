import pytest
from app.nutrition.allergens import match_allergens

def test_groundnut_oil_vs_peanut_allergy():
    passport = {"allergies": ["peanuts"], "diet_type": "non-veg"}
    findings = match_allergens("Sauté the vegetables in groundnut oil for extra flavor.", passport)
    assert len(findings) > 0
    assert findings[0].conflicts_with == "allergy: peanuts"
    assert "groundnut oil" in findings[0].phrase

def test_ghee_vs_dairy_allergy():
    passport = {"allergies": ["dairy"], "diet_type": "veg"}
    findings = match_allergens("Add a spoonful of desi ghee on top of hot rice.", passport)
    assert len(findings) > 0
    assert findings[0].conflicts_with == "allergy: dairy"

def test_jowar_roti_vs_gluten_allergy():
    passport = {"allergies": ["gluten"], "diet_type": "veg"}
    findings = match_allergens("Enjoy with jowar roti and dal.", passport)
    assert len(findings) == 0

def test_paneer_vs_vegan():
    passport = {"allergies": [], "diet_type": "vegan"}
    findings = match_allergens("Eat paneer tikka for high protein.", passport)
    assert len(findings) > 0
    assert findings[0].conflicts_with == "diet_type: vegan"

def test_peanut_chutney_vs_peanut_allergy():
    passport = {"allergies": ["peanuts"], "diet_type": "veg"}
    findings = match_allergens("Add peanut chutney on the side, it tastes great!", passport)
    assert len(findings) > 0
    assert "peanut chutney" in findings[0].phrase
