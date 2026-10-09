import os
import json
from datetime import datetime, timezone
from PIL import Image, ImageDraw
from sqlmodel import Session, select
from app.db import engine, init_db
from app.models import User, Passport, Community, Post, Reply, LabelProduct


def _ensure_placeholder_photo(path: str, bg_color: tuple[int, int, int], accent_color: tuple[int, int, int], label: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path):
        return path

    image = Image.new("RGB", (1200, 900), bg_color)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 80, 1120, 820), radius=40, fill=accent_color)
    draw.rectangle((150, 150, 1050, 750), fill=(255, 255, 255, 128))
    draw.text((200, 350), label, fill=(20, 20, 20), font=None)
    image.save(path, "JPEG", quality=90)
    return path


def run_seed():
    init_db()
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("seed/sample_images", exist_ok=True)
    sample_biscuit_path = _ensure_placeholder_photo(
        "uploads/sample_biscuit.jpg",
        (250, 233, 202),
        (220, 185, 100),
        "NutriChoice\nDigestive Biscuit"
    )
    sample_thali_path = _ensure_placeholder_photo(
        "uploads/sample_thali.jpg",
        (211, 232, 206),
        (116, 179, 94),
        "Healthy Meal\nThali"
    )

    with Session(engine) as session:
        # Check if users already seeded
        existing_users = session.exec(select(User)).all()
        if existing_users:
            print("Database already contains data. Skipping seed.")
            return

        print("Seeding demo users and passports...")
        
        # 1. Seed Users & Passports
        aarav = User(
            name="Aarav Sharma",
            role="member",
            is_verified=False,
            credential_note="Hostel Student",
            reputation=10,
            language="en",
            avatar_color="bg-amber-600"
        )
        session.add(aarav)
        session.commit()
        session.refresh(aarav)

        passport_aarav = Passport(
            user_id=aarav.id,
            allergies_raw=json.dumps(["peanuts"]),
            diet_type="veg",
            avoid_list_raw=json.dumps(["palm oil"]),
            goals_raw=json.dumps(["low sugar", "high protein"]),
            conditions_note="Slight mild acid reflux occasionally",
            budget_note="Student budget (~₹150/day snacks)",
            language="en"
        )
        session.add(passport_aarav)

        meera = User(
            name="Meera Patel",
            role="member",
            is_verified=False,
            credential_note="Fitness Enthusiast",
            reputation=25,
            language="hi",
            avatar_color="bg-emerald-600"
        )
        session.add(meera)
        session.commit()
        session.refresh(meera)

        passport_meera = Passport(
            user_id=meera.id,
            allergies_raw=json.dumps([]),
            diet_type="vegan",
            avoid_list_raw=json.dumps(["dairy", "honey"]),
            goals_raw=json.dumps(["bulk", "high protein"]),
            conditions_note="Weight ~60 kg; bulking phase",
            budget_note="Flexible",
            language="hi"
        )
        session.add(passport_meera)

        kiran = User(
            name="Kiran Kumar",
            role="member",
            is_verified=False,
            credential_note="Engineering Student",
            reputation=5,
            language="kn",
            avatar_color="bg-blue-600"
        )
        session.add(kiran)
        session.commit()
        session.refresh(kiran)

        passport_kiran = Passport(
            user_id=kiran.id,
            allergies_raw=json.dumps([]),
            diet_type="non-veg",
            avoid_list_raw=json.dumps([]),
            goals_raw=json.dumps(["tone", "high protein"]),
            conditions_note="Weight ~70 kg; toning goal",
            budget_note="Hostel mess subscriber",
            language="kn"
        )
        session.add(passport_kiran)

        riya = User(
            name="Riya Sen",
            role="peer",
            is_verified=False,
            credential_note="Senior Peer Contributor",
            reputation=40,
            language="en",
            avatar_color="bg-indigo-600"
        )
        session.add(riya)

        dev = User(
            name="Dev Raj",
            role="peer",
            is_verified=False,
            credential_note="Active Community Member",
            reputation=15,
            language="en",
            avatar_color="bg-slate-600"
        )
        session.add(dev)

        nisha = User(
            name="Dr. Nisha Rao",
            role="dietitian",
            is_verified=True,
            credential_note="Registered Dietitian (demo account)",
            reputation=120,
            language="en",
            avatar_color="bg-teal-600"
        )
        session.add(nisha)

        imran = User(
            name="Dr. Imran Shaikh",
            role="dietitian",
            is_verified=True,
            credential_note="Clinical Nutritionist (demo account)",
            reputation=95,
            language="en",
            avatar_color="bg-cyan-600"
        )
        session.add(imran)

        admin = User(
            name="System Admin",
            role="admin",
            is_verified=True,
            credential_note="URFeast Admin",
            reputation=500,
            language="en",
            avatar_color="bg-purple-600"
        )
        session.add(admin)

        session.commit()

        # 2. Seed Communities
        comm_mess = Community(
            name="MSRIT Hostel Mess",
            kind="hostel_mess",
            description="Daily mess menu feedback, substitutions, and nutrition checks for hostelers"
        )
        comm_canteen = Community(
            name="Campus Canteen",
            kind="canteen",
            description="Quick bites, packed snacks, and beverages available around campus"
        )
        comm_general = Community(
            name="General",
            kind="general",
            description="General nutrition questions, packaged-food label scanning, and diet guidance"
        )
        session.add_all([comm_mess, comm_canteen, comm_general])
        session.commit()
        session.refresh(comm_mess)
        session.refresh(comm_canteen)
        session.refresh(comm_general)

        # 3. Seed Label Product
        biscuit_label = LabelProduct(
            name_guess="NutriChoice Digestive Biscuit",
            barcode="8901063012345",
            label_json_raw=json.dumps({
                "product_name": "NutriChoice Digestive Biscuit",
                "serving_size_g": 25,
                "servings_per_pack": 4,
                "per_100g": {
                    "energy_kcal": 460,
                    "sugar_g": 18.0,
                    "sodium_mg": 380,
                    "fat_g": 19.0,
                    "protein_g": 8.5
                },
                "per_serving": {
                    "energy_kcal": 115,
                    "sugar_g": 4.5,
                    "sodium_mg": 95,
                    "fat_g": 4.75,
                    "protein_g": 2.1
                },
                "ingredients": ["Whole Wheat Flour (Atta)", "Vegetable Oil (Palm)", "Sugar", "Wheat Bran", "Raising Agents"],
                "allergen_statement": "Contains Wheat (Gluten). May contain traces of Nuts and Milk."
            }),
            scanned_by=aarav.id,
            scan_count=3
        )
        session.add(biscuit_label)
        session.commit()
        session.refresh(biscuit_label)

        # 4. Seed Posts
        post1_analysis = {
            "image_kind_detected": "label",
            "verdict": "okay_with_changes",
            "summary": "This biscuit contains whole wheat and no peanuts listed in the main ingredients. However, it contains palm oil and 4.5g of sugar per serving (about 1.1 teaspoons). Limit your portion to 2 biscuits.",
            "observations": [
                {
                    "text": "Product name printed as NutriChoice Digestive",
                    "evidence": "printed_on_label",
                    "quote": "NutriChoice Digestive Biscuit 100g",
                    "box": [100, 200, 300, 800]
                },
                {
                    "text": "Ingredients list whole wheat flour, palm oil, sugar",
                    "evidence": "printed_on_label",
                    "quote": "Ingredients: Whole Wheat Flour (55%), Vegetable Oil (Palm Oil), Sugar",
                    "box": [400, 150, 700, 850]
                },
                {
                    "text": "Peanuts not listed in main ingredients",
                    "evidence": "printed_on_label",
                    "quote": "May contain traces of Nuts",
                    "box": [720, 150, 800, 850]
                },
                {
                    "text": "Peanut chutney or fresh peanut butter",
                    "evidence": "not_visible",
                    "quote": None,
                    "box": None
                }
            ],
            "possible_conflicts": [
                {
                    "item": "palm oil",
                    "reason": "Listed in your Passport avoid list; ingredient contains palm oil",
                    "severity": "medium",
                    "evidence_quote": "Vegetable Oil (Palm Oil)"
                }
            ],
            "label_data": {
                "product_name": "NutriChoice Digestive Biscuit",
                "serving_size_g": 25,
                "servings_per_pack": 4,
                "per_100g": {
                    "energy_kcal": 460,
                    "sugar_g": 18.0,
                    "sodium_mg": 380,
                    "fat_g": 19.0,
                    "protein_g": 8.5
                },
                "per_serving": {
                    "energy_kcal": 115,
                    "sugar_g": 4.5,
                    "sodium_mg": 95,
                    "fat_g": 4.75,
                    "protein_g": 2.1
                },
                "ingredients": ["Whole Wheat Flour", "Palm Oil", "Sugar", "Wheat Bran"],
                "allergen_statement": "May contain traces of Nuts"
            },
            "swap_suggestions": [
                "Swap for roasted chana or plain oats chilla for lower sugar and no palm oil",
                "Limit to 2 biscuits instead of the full pack of 4"
            ],
            "needs_dietitian": False,
            "unreadable_regions": [],
            "follow_up_questions": ["Would you like a homemade low-sugar biscuit recipe?"],
            "disclaimer_shown": True
        }

        post1 = Post(
            author_id=aarav.id,
            image_path=sample_biscuit_path,
            image_kind="label",
            question_text="Is this multi-grain biscuit okay for my afternoon snack? Does it contain peanuts or high sugar?",
            created_at=datetime.now(timezone.utc),
            community_id=comm_canteen.id,
            status="dietitian_approved",
            analysis_json_raw=json.dumps(post1_analysis),
            label_product_id=biscuit_label.id
        )
        session.add(post1)
        session.commit()
        session.refresh(post1)

        # 5. Seed Replies for Post 1 (including unsafe peer suggestion)
        reply_peer_unsafe = Reply(
            post_id=post1.id,
            author_id=riya.id,
            author_type="peer",
            body="Add peanut chutney on the side",
            created_at=datetime.now(timezone.utc),
            audit_json_raw=json.dumps({
                "status": "unsafe",
                "findings": [
                    {
                        "phrase": "peanut chutney",
                        "conflicts_with": "allergy: peanuts",
                        "reason": "Peanut chutney contains peanuts which triggers the poster's severe peanut allergy.",
                        "severity": "high"
                    }
                ],
                "safer_alternative": "Suggest almond butter or coconut chutney instead.",
                "user_message": "Conflicts with poster's severe peanut allergy: peanut chutney contains peanuts. Do not follow."
            }),
            audit_status="unsafe",
            helpful_votes=0
        )

        reply_dietitian_safe = Reply(
            post_id=post1.id,
            author_id=nisha.id,
            author_type="dietitian",
            body="Good choice on whole wheat! No peanuts are in the ingredient list. However, 18g sugar per 100g means 2 biscuits give ~2.3g sugar. Stick to 2 biscuits max to keep sugar under your goal limit.",
            created_at=datetime.now(timezone.utc),
            audit_json_raw=json.dumps({
                "status": "safe",
                "findings": [],
                "safer_alternative": None,
                "user_message": "Checked against poster's Diet Passport: safe for peanut allergy & low sugar goal."
            }),
            audit_status="safe",
            helpful_votes=5
        )

        session.add_all([reply_peer_unsafe, reply_dietitian_safe])

        # Post 2 for Meera
        post2 = Post(
            author_id=meera.id,
            image_path=sample_thali_path,
            image_kind="meal",
            question_text="इस थाली में वीगन प्रोटीन के लिए कौन सी डिश सबसे अच्छी है?",
            created_at=datetime.now(timezone.utc),
            community_id=comm_mess.id,
            status="answered",
            analysis_json_raw=json.dumps({
                "image_kind_detected": "meal",
                "verdict": "good_fit",
                "summary": "यह थाली काफी पौष्टिक है। दाल और चना करी वीगन प्रोटीन के उत्कृष्ट स्रोत हैं। दही को छोड़ दें ताकि यह पूरी तरह से वीगन रहे।",
                "observations": [
                    {"text": "Yellow Dal Tadka observed on upper bowl", "evidence": "seen_on_plate", "quote": None, "box": None},
                    {"text": "Black Chana Masala observed on right bowl", "evidence": "seen_on_plate", "quote": None, "box": None},
                    {"text": "Curd (Dahi) bowl present", "evidence": "seen_on_plate", "quote": None, "box": None}
                ],
                "possible_conflicts": [
                    {"item": "curd", "reason": "Dairy product conflicts with Vegan diet type", "severity": "medium", "evidence_quote": None}
                ],
                "label_data": {},
                "swap_suggestions": ["दही की जगह नींबू पानी या extra सलाद लें"],
                "needs_dietitian": False,
                "unreadable_regions": [],
                "follow_up_questions": [],
                "disclaimer_shown": True
            })
        )
        session.add(post2)
        session.commit()

        post3 = Post(
            author_id=kiran.id,
            image_path=sample_thali_path,
            image_kind="meal",
            question_text="ಈ ಊಟದಲ್ಲಿ ಪ್ರೋಟೀನ್ ಎಷ್ಟು ಇದೆ? ಟೋನ್ ಗೋಲ್‌ಗೆ ಸರಿಹೊಂದುತ್ತದೆಯೇ?",
            created_at=datetime.now(timezone.utc),
            community_id=comm_general.id,
            status="open",
            analysis_json_raw=json.dumps({
                "image_kind_detected": "meal",
                "verdict": "okay_with_changes",
                "summary": "Thali looks balanced. Dal and roti give moderate protein; add curd or egg whites if you eat eggs for toning goals.",
                "observations": [
                    {"text": "Two rotis on plate", "evidence": "seen_on_plate", "quote": None},
                    {"text": "Dal bowl visible", "evidence": "seen_on_plate", "quote": None},
                ],
                "label_data": {},
                "swap_suggestions": ["Add a bowl of curd or sprouts for extra protein"],
                "needs_dietitian": False,
            }),
        )
        session.add(post3)
        session.commit()

        # Seed initial Final Plan for Post 1
        post1.final_plan_json_raw = json.dumps({
            "bullets": [
                {"text": "No peanuts listed in ingredients; safe for your peanut allergy. (dietitian)", "source": "dietitian"},
                {"text": "Limit portion to 2 biscuits max (4.5g sugar total) for your low sugar goal. (dietitian)", "source": "dietitian"},
                {"text": "Contains palm oil; avoid if strictly eliminating palm oil. (ai)", "source": "ai"}
            ],
            "check_line": "Check ingredient panel on future batches for allergen trace warnings.",
            "language": "en"
        })
        session.add(post1)
        session.commit()

        print("Database successfully seeded with demo data!")

if __name__ == "__main__":
    run_seed()
