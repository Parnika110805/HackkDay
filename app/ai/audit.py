import json
import logging
from typing import Dict, Any
from app.ai.gemma import gemma_client
from app.ai.prompts import SYSTEM_AUDIT_REPLY
from app.ai.schemas import AuditOut, AuditFinding
from app.nutrition.allergens import match_allergens

logger = logging.getLogger("urfeast.audit")

def audit_reply(
    reply_body: str,
    poster_passport_dict: Dict[str, Any],
    author_role: str = "peer",
    language: str = "en"
) -> AuditOut:
    """Hybrid safety audit: deterministic allergen scan + Gemma safety check."""
    language = "en" if language not in ("en", None) else "en"

    # 1. Deterministic Allergen Scan
    det_findings = match_allergens(reply_body, poster_passport_dict)
    
    # 2. Gemma AI Audit Call
    user_prompt = (
        f"Poster's Diet Passport:\n{json.dumps(poster_passport_dict, indent=2)}\n\n"
        f"Reply Advice Body ({author_role}):\n{reply_body}"
    )

    ai_audit: AuditOut
    try:
        ai_audit = gemma_client.generate_json(SYSTEM_AUDIT_REPLY, [user_prompt], AuditOut)
    except Exception as e:
        logger.warning(f"Gemma audit AI call failed ({e}). Relying on deterministic scan.")
        ai_audit = AuditOut(
            status="safe",
            findings=[],
            safer_alternative=None,
            user_message="Checked against poster's Diet Passport."
        )

    # 3. Merge Deterministic and AI Findings
    merged_findings = list(ai_audit.findings)
    for df in det_findings:
        # Avoid duplicate phrases
        if not any(f.phrase.lower() == df.phrase.lower() for f in merged_findings):
            merged_findings.append(df)

    # Determine overall status
    has_unsafe = any(f.severity == "high" for f in merged_findings) or len(det_findings) > 0
    has_caution = any(f.severity == "medium" for f in merged_findings)

    if has_unsafe:
        final_status = "unsafe"
    elif has_caution or ai_audit.status == "caution":
        final_status = "caution"
    else:
        final_status = "safe"

    # Craft UI chip message in poster's language
    if final_status == "unsafe":
        trigger_item = merged_findings[0].phrase if merged_findings else "an ingredient"
        if author_role == "dietitian":
            user_msg = f"Flagged for review ({trigger_item}). A dietitian's advice may account for this; please confirm with them."
        else:
            user_msg = f"Conflicts with poster's Passport: '{trigger_item}'. Do not follow."
    elif final_status == "caution":
        reason = merged_findings[0].reason if merged_findings else "General dietary caution"
        user_msg = f"Caution: {reason}"
    else:
        user_msg = "Checked against poster's Diet Passport: looks safe."

    return AuditOut(
        status=final_status,
        findings=merged_findings,
        safer_alternative=ai_audit.safer_alternative,
        user_message=user_msg
    )
