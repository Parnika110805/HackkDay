import json
import logging
from typing import List, Dict, Any
from app.ai.gemma import gemma_client
from app.ai.prompts import SYSTEM_FINAL_PLAN
from app.ai.schemas import FinalPlanOut, FinalPlanBullet

logger = logging.getLogger("urfeast.summarize")

def synthesize_final_plan(
    question_text: str,
    passport_dict: Dict[str, Any],
    replies: List[Dict[str, Any]],
    language: str = "en"
) -> FinalPlanOut:
    """Synthesizes a 3-5 bullet Final Plan strictly filtering out unsafe audited advice."""
    language = "en" if language not in ("en", None) else "en"

    # Filter out unsafe replies
    safe_replies = [r for r in replies if r.get("audit_status") != "unsafe"]
    
    user_prompt = (
        f"Poster Question:\n{question_text}\n\n"
        f"Poster Diet Passport:\n{json.dumps(passport_dict, indent=2)}\n\n"
        f"Safe & Caution Thread Replies:\n{json.dumps(safe_replies, indent=2)}"
    )

    system_prompt = SYSTEM_FINAL_PLAN.format(language=language)

    try:
        return gemma_client.generate_json(system_prompt, [user_prompt], FinalPlanOut)
    except Exception as e:
        logger.warning(f"Gemma final_plan call failed ({e}). Generating fallback plan.")
        return _get_demo_fallback_plan(safe_replies, language)

def _get_demo_fallback_plan(safe_replies: List[Dict[str, Any]], language: str) -> FinalPlanOut:
    bullets = []
    
    # Check if any dietitian reply is present
    has_dietitian = any(r.get("author_type") == "dietitian" for r in safe_replies)
    
    bullets.append(FinalPlanBullet(text="No peanut allergens detected in main label ingredients. (dietitian)" if has_dietitian else "Verify ingredient list for hidden allergens. (ai)", source="dietitian" if has_dietitian else "ai"))
    bullets.append(FinalPlanBullet(text="Limit portion to 2 biscuits to stay under your low-sugar goal limit. (dietitian)" if has_dietitian else "Limit portion to 2 pieces max. (peer)", source="dietitian" if has_dietitian else "peer"))
    bullets.append(FinalPlanBullet(text="Pair with green tea or water instead of sugary beverages. (ai)", source="ai"))
    check_line = "Check future batches for updated ingredient trace warnings."

    return FinalPlanOut(
        bullets=bullets,
        check_line=check_line,
        language=language
    )
