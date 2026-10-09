import re
from typing import List, Dict, Any
from app.ai.schemas import AuditFinding

ALLERGEN_SYNONYMS: Dict[str, List[str]] = {
    "peanuts": [
        "peanut", "peanuts", "groundnut", "groundnuts", "arachis",
        "peanut oil", "groundnut oil", "arachis oil", "peanut butter",
        "peanut chutney", "shengdana", "moongfali", "chikki"
    ],
    "tree nuts": [
        "tree nut", "tree nuts", "almond", "almonds", "cashew", "cashews",
        "pista", "pistachio", "pistachios", "walnut", "walnuts", "hazelnut",
        "hazelnuts", "pecan", "macadamia", "badam", "kaju", "akhrot"
    ],
    "dairy": [
        "dairy", "milk", "ghee", "paneer", "curd", "dahi", "butter", "whey",
        "casein", "khoa", "khoya", "cheese", "cream", "yogurt", "yoghurt",
        "malai", "milk powder", "condensed milk", "butter oil", "skimmed milk",
        "lassi", "buttermilk", "chaas", "rabri", "kheer", "makhani"
    ],
    "gluten": [
        "gluten", "wheat", "atta", "maida", "semolina", "rava", "suji", "sooji",
        "barley", "rye", "bread", "biscuit", "roti", "paratha", "naan", "puri",
        "poori", "bhatura", "noodles", "pasta", "couscous", "wheat bran",
        "all-purpose flour", "whole wheat"
    ],
    "soy": [
        "soy", "soya", "tofu", "edamame", "soy sauce", "soya sauce",
        "soya chunks", "soy lecithin", "soya lecithin", "soy protein", "soya bean"
    ],
    "egg": [
        "egg", "eggs", "egg white", "egg yolk", "albumin", "egg powder",
        "mayonnaise", "mayo", "omelette", "anda"
    ],
    "fish": [
        "fish", "surimi", "anchovy", "salmon", "tuna", "fish sauce",
        "machhli", "machli"
    ],
    "shellfish": [
        "shellfish", "prawn", "prawns", "shrimp", "shrimps", "crab",
        "lobster", "clam", "mussel", "oyster", "squid", "jhinga"
    ],
    "sesame": [
        "sesame", "til", "tahini", "til oil", "gingelly", "gingelly oil"
    ],
    "mustard": [
        "mustard", "sarson", "sarson oil", "rai", "mustard oil", "mustard paste"
    ]
}

# Diet type forbidden ingredients mapping
DIET_FORBIDDEN: Dict[str, List[str]] = {
    "veg": ["chicken", "mutton", "fish", "prawn", "egg", "beef", "pork", "meat"],
    "vegan": ["chicken", "mutton", "fish", "prawn", "egg", "beef", "pork", "meat", "milk", "ghee", "paneer", "curd", "dahi", "butter", "cheese", "honey", "malai"],
    "egg": ["chicken", "mutton", "fish", "prawn", "beef", "pork", "meat"],
    "jain": ["onion", "garlic", "potato", "carrot", "radish", "root vegetable", "chicken", "mutton", "fish", "egg"]
}

def match_allergens(text: str, passport_dict: Dict[str, Any]) -> List[AuditFinding]:
    """Scans human advice text deterministically against poster's Passport allergies and diet type."""
    findings: List[AuditFinding] = []
    text_lower = text.lower()
    
    allergies = passport_dict.get("allergies", [])
    diet_type = passport_dict.get("diet_type", "").lower()
    
    # Gluten-free exceptions (e.g. jowar roti, bajra roti, ragi roti)
    gluten_free_rotis = ["jowar roti", "bajra roti", "ragi roti", "millet roti", "jowar", "bajra", "ragi"]

    # 1. Check Allergies
    for allergy in allergies:
        alg_key = allergy.lower()
        synonyms = ALLERGEN_SYNONYMS.get(alg_key, [alg_key])
        
        # Sort synonyms by length descending so multi-word phrases (e.g. groundnut oil) match before single words (groundnut)
        synonyms = sorted(synonyms, key=lambda s: len(s), reverse=True)
        
        for syn in synonyms:
            # Skip false gluten flagging if phrase matches a gluten-free millet roti
            if alg_key == "gluten" and syn == "roti":
                if any(gf in text_lower for gf in gluten_free_rotis):
                    continue

            pattern = r'\b' + re.escape(syn) + r'\b'
            if re.search(pattern, text_lower):
                findings.append(AuditFinding(
                    phrase=syn,
                    conflicts_with=f"allergy: {allergy}",
                    reason=f"Advice contains '{syn}' which conflicts with the poster's severe {allergy} allergy.",
                    severity="high"
                ))
                break

    # 2. Check Diet Type Conflicts
    forbidden = DIET_FORBIDDEN.get(diet_type, [])
    for item in forbidden:
        pattern = r'\b' + re.escape(item) + r'\b'
        if re.search(pattern, text_lower):
            severity = "high" if diet_type in ["vegan", "jain", "veg"] else "medium"
            findings.append(AuditFinding(
                phrase=item,
                conflicts_with=f"diet_type: {diet_type}",
                reason=f"Advice contains '{item}' which conflicts with the poster's {diet_type} diet.",
                severity=severity
            ))

    return findings
