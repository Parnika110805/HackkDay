from typing import Optional, Dict, Any

def pack_total(per_serving_value: Optional[float], servings_per_pack: Optional[float]) -> Optional[float]:
    """Computes total nutrient value for the full package."""
    if per_serving_value is None or servings_per_pack is None:
        return None
    try:
        return round(float(per_serving_value) * float(servings_per_pack), 2)
    except (ValueError, TypeError):
        return None

def per_serving_from_100g(per_100g_value: Optional[float], serving_size_g: Optional[float]) -> Optional[float]:
    """Computes per serving value given per 100g value and serving size in grams."""
    if per_100g_value is None or serving_size_g is None:
        return None
    try:
        return round((float(per_100g_value) * float(serving_size_g)) / 100.0, 2)
    except (ValueError, TypeError):
        return None

def per_100g_from_serving(per_serving_value: Optional[float], serving_size_g: Optional[float]) -> Optional[float]:
    """Computes per 100g value given per serving value and serving size in grams."""
    if per_serving_value is None or serving_size_g is None or float(serving_size_g) == 0:
        return None
    try:
        return round((float(per_serving_value) * 100.0) / float(serving_size_g), 2)
    except (ValueError, TypeError):
        return None

def sugar_in_teaspoons(sugar_g: Optional[float]) -> Optional[float]:
    """Converts sugar in grams to teaspoons (assumption: 1 tsp ~ 4.0 grams)."""
    if sugar_g is None:
        return None
    try:
        return round(float(sugar_g) / 4.0, 1)
    except (ValueError, TypeError):
        return None

def sodium_mg_to_salt_g(sodium_mg: Optional[float]) -> Optional[float]:
    """Converts sodium in milligrams to equivalent salt in grams (salt_g = sodium_mg * 2.5 / 1000)."""
    if sodium_mg is None:
        return None
    try:
        return round((float(sodium_mg) * 2.5) / 1000.0, 2)
    except (ValueError, TypeError):
        return None

def compare_two(label_a: Dict[str, Any], label_b: Dict[str, Any]) -> Dict[str, Any]:
    """Compares per 100g values between two label data dicts."""
    nutrients = ["energy_kcal", "sugar_g", "sodium_mg", "fat_g", "protein_g"]
    a_per100 = label_a.get("per_100g") or {}
    b_per100 = label_b.get("per_100g") or {}

    comparison = {}
    for nut in nutrients:
        val_a = a_per100.get(nut)
        val_b = b_per100.get(nut)
        if val_a is not None and val_b is not None and float(val_a) > 0:
            diff_pct = round(((float(val_b) - float(val_a)) / float(val_a)) * 100.0, 1)
        else:
            diff_pct = None
        comparison[nut] = {
            "a": val_a,
            "b": val_b,
            "diff_pct": diff_pct
        }
    return comparison
