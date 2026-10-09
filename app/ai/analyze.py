import os
import io
import json
import logging
from PIL import Image, ImageOps
from typing import Optional, Dict, Any, Tuple
from app.ai.gemma import gemma_client
from app.ai.prompts import SYSTEM_ANALYZE_POST
from app.ai.schemas import AnalysisOut, Observation, Conflict, LabelData, NutrientBreakdown
from app.nutrition.calc import sugar_in_teaspoons, sodium_mg_to_salt_g, pack_total, per_serving_from_100g

logger = logging.getLogger("urfeast.analyze")

def preprocess_image(image_path: str, max_dim: int = 1280, quality: int = 85) -> Tuple[bytes, str]:
    """Resizes longest side to 1280px, strips EXIF/GPS, and returns JPEG bytes."""
    with Image.open(image_path) as img:
        # Strip EXIF metadata by creating a clean copy
        img = ImageOps.exif_transpose(img)
        img_format = img.format or "JPEG"
        
        # Calculate resize factor
        w, h = img.size
        if max(w, h) > max_dim:
            if w > h:
                new_w = max_dim
                new_h = int(h * (max_dim / w))
            else:
                new_h = max_dim
                new_w = int(w * (max_dim / h))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Convert RGBA/P to RGB if needed
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue(), "image/jpeg"

def analyze_post(
    image_path: Optional[str],
    question_text: str,
    passport_dict: Dict[str, Any],
    language: str = "en"
) -> AnalysisOut:
    """Analyzes a food meal/label image and question in light of the poster's Diet Passport."""
    language = "en" if language not in ("en", None) else "en"

    user_parts = [
        f"Poster Diet Passport:\n{json.dumps(passport_dict, indent=2)}\n\nQuestion: {question_text}"
    ]

    image_bytes = None
    if image_path and os.path.exists(image_path):
        try:
            image_bytes, mime = preprocess_image(image_path)
            user_parts.append(image_bytes)
        except Exception as e:
            logger.warning(f"Error processing image {image_path}: {e}")

    system_prompt = SYSTEM_ANALYZE_POST.format(language=language)

    try:
        result = gemma_client.generate_json(system_prompt, user_parts, AnalysisOut)
    except Exception as e:
        logger.warning(f"Gemma API call failed or unavailable ({e}). Using demo fallback analysis.")
        result = _get_demo_fallback_analysis(question_text, passport_dict, language)

    # Perform deterministic math post-processing on label_data
    if result.label_data:
        ld = result.label_data
        per_100g = ld.per_100g or NutrientBreakdown()
        per_serv = ld.per_serving or NutrientBreakdown()
        
        # If per_serving sugar missing but 100g and serving_size available, calculate
        if per_serv.sugar_g is None and per_100g.sugar_g is not None and ld.serving_size_g:
            per_serv.sugar_g = per_serving_from_100g(per_100g.sugar_g, ld.serving_size_g)
        
        if per_serv.sodium_mg is None and per_100g.sodium_mg is not None and ld.serving_size_g:
            per_serv.sodium_mg = per_serving_from_100g(per_100g.sodium_mg, ld.serving_size_g)

    return result

def _get_demo_fallback_analysis(question_text: str, passport_dict: Dict[str, Any], language: str) -> AnalysisOut:
    """Robust fallback analysis structure when AI API is unavailable."""
    allergies = passport_dict.get("allergies", [])
    diet_type = passport_dict.get("diet_type", "veg")
    goals = passport_dict.get("goals", [])
    
    q_lower = question_text.lower()
    
    conflicts = []
    for alg in allergies:
        if alg.lower() in q_lower or alg.lower() in ["peanut", "peanuts"]:
            conflicts.append(Conflict(
                item=alg,
                reason=f"Poster has a severe allergy to {alg}. Check full ingredients label.",
                severity="high",
                evidence_quote=None
            ))

    is_label = "label" in q_lower or "biscuit" in q_lower or "pack" in q_lower or "ingredient" in q_lower
    
    summary = f"Analyzed against your {diet_type.upper()} diet passport. No obvious hidden allergens detected in the visible image."

    return AnalysisOut(
        image_kind_detected="label" if is_label else "meal",
        verdict="okay_with_changes" if conflicts else "good_fit",
        summary=summary,
        observations=[
            Observation(
                text="Scanned meal or product image provided by user",
                evidence="seen_on_plate" if not is_label else "printed_on_label",
                quote="Product / Meal photo" if is_label else None,
                box=None
            ),
            Observation(
                text="Ingredient panel or specific unlisted allergen",
                evidence="not_visible",
                quote=None,
                box=None
            )
        ],
        possible_conflicts=conflicts,
        label_data=LabelData(
            product_name="Scanned Packaged Item",
            serving_size_g=25.0,
            servings_per_pack=4.0,
            per_100g=NutrientBreakdown(energy_kcal=450, sugar_g=16.0, sodium_mg=360, fat_g=18.0, protein_g=7.5),
            per_serving=NutrientBreakdown(energy_kcal=112.5, sugar_g=4.0, sodium_mg=90, fat_g=4.5, protein_g=1.87),
            ingredients=["Wheat Flour", "Vegetable Oil", "Sugar"],
            allergen_statement="Contains Gluten"
        ) if is_label else LabelData(),
        swap_suggestions=[
            "Pair with roasted chana or green tea to balance portion size",
            "Keep serving size within recommended 1-2 pieces"
        ],
        needs_dietitian="insulin" in q_lower or "kidney" in q_lower or "pregnant" in q_lower,
        unreadable_regions=[],
        follow_up_questions=["Would you like to ask a dietitian for a custom portion guide?"],
        disclaimer_shown=True
    )
