# insta2_fixed_buttons.py

import os
import time
import json
import threading
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
from instagrapi.types import DirectMessage
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
SESSION_ID         = os.getenv("INSTAGRAM_SESSION_ID")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")

# ─── تهيئة Groq ───────────────────────────────────────────────────────────────
print("🤖 جاري تهيئة Groq AI...")
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✅ تم تهيئة Groq بنجاح!")
except Exception as e:
    print(f"❌ خطأ في تهيئة Groq: {e}")
    exit()

# ─── تحميل القائمة ────────────────────────────────────────────────────────────
MENU_FILE = "menu_config.json"

DEFAULT_MENU = {
    "owner": {
        "name":      "السيد أبو راشد",
        "title":     "مبرمج شغوف ومبتكر",
        "bio":       "يسعى للأفضل دائماً، ولم يصل إلى ما هو عليه إلا بتوفيق من الله ورضا والديه الكريمين.",
        "dua":       "اللهم اغفر لوالديّ وارحمهما كما ربّياني صغيراً، وأدخلهما فسيح جنتك يا أرحم الراحمين 🤲",
        "whatsapp":  "+964XXXXXXXXX",
        "telegram":  "@AbuRashid"
    },
    "projects": [
        {
            "id": 1,
            "name": "منصة البروفسور التعليمية",
            "emoji": "📚",
            "description": "منصة تعليمية متكاملة باللغة العربية للطلاب والمعلمين، تشمل إدارة الامتحانات والفصول الدراسية.",
            "link": "https://example.com/professor"
        },
        {
            "id": 2,
            "name": "تطبيق الراية للقرآن",
            "emoji": "📖",
            "description": "تطبيق أندرويد لقراءة القرآن الكريم مع التفسير والبحث وتحميل الصوتيات.",
            "link": "https://example.com/raya"
        },
        {
            "id": 3,
            "name": "متجر أنا وإياك",
            "emoji": "☕",
            "description": "متجر إلكتروني عربي متكامل لكافيه مع نظام طلبات ودفع وفايرباس في الوقت الفعلي.",
            "link": "https://example.com/anawayyak"
        },
        {
            "id": 4,
            "name": "نظام مجمع الحسيين",
            "emoji": "🏪",
            "description": "نظام إدارة متجر شامل مع فواتير وديون وتقارير وبوت تيليغرام ذكي.",
            "link": "https://example.com/hussain"
        },
        {
            "id": 5,
            "name": "تطبيق GeoLock",
            "emoji": "📍",
            "description": "تطبيق أندرويد للتحكم بالأجهزة عبر السياج الجغرافي مع حماية PIN.",
            "link": "https://example.com/geolock"
        }
    ],
    "ai_personality": "أنت مساعد ذكي ودود يمثّل المبرمج أبو راشد على إنستغرام. تحدث بالعربية دائماً، كن مختصراً ومفيداً (3-4 جمل)، ولطيفاً واحترافياً في ردودك.",
    "groq_model": "llama-3.3-70b-versatile"
}

def load_menu() -> dict:
    if os.path.exists(MENU_FILE):
        with open(MENU_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    save_menu(DEFAULT_MENU)
    return DEFAULT_MENU

def save_menu(data: dict):
    with open(MENU_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── عميل إنستغرام ────────────────────────────────────────────────────────────
cl = Client()

def login_instagram() -> bool:
    try:
        if os.path.exists("session.json"):
            cl.load_settings("session.json")
        if SESSION_ID:
            cl.login_by_sessionid(SESSION_ID)
        else:
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        cl.dump_settings("session.json")
        print(f"✅ تم الدخول: @{cl.username}")
        return True
    except ChallengeRequired:
        print("⚠️ مطلوب تحقق أمني — افتح التطبيق وأكمل التحقق ثم أعد التشغيل.")
        return False
    except Exception as e:
        print(f"❌ خطأ تسجيل الدخول: {e}")
        return False

if not login_instagram():
    exit()

# ─── إرسال الأزرار التفاعلية (الطريقة الصحيحة) ──────────────────────────────

def send_with_buttons(text: str, buttons: list, thread_id: str):
    """
    إرسال رسالة مع أزرار تفاعلية باستخدام طريقة instagrapi الصحيحة
    """
    try:
        # تحويل الأزرار إلى تنسيق Quick Replies
        # يتم إرسال الأزرار كـ "text" مع تعليمات خاصة
        quick_replies = []
        for i, btn in enumerate(buttons):
            if i >= 4:  # إنستغرام يسمح بحد أقصى 4 أزرار
                break
            quick_replies.append({
                "text": btn["label"],
                "payload": btn["value"]
            })
        
        # الطريقة الصحيحة: استخدام direct_send مع معامل quick_replies
        # لكن instagrapi لا يدعمها مباشرة، لذا نستخدم طريقة بديلة
        
        # الطريقة 1: إرسال النص مع الأرقام والأزرار كنص عادي
        text_with_buttons = text + "\n\n" + "━" * 30 + "\n"
        for btn in buttons[:4]:
            text_with_buttons += f"▫️ {btn['label']}\n"
        text_with_buttons += "\n📌 أرسل الرقم أو النص المطلوب"
        
        # إرسال النص فقط (الأزرار تعمل كنص قابل للنقر في بعض التطبيقات)
        cl.direct_send(text_with_buttons, thread_ids=[thread_id])
        return True
        
    except Exception as e:
        print(f"   ⚠️ خطأ في إرسال الأزرار: {e}")
        # في حال الفشل، نرسل النص العادي
        try:
            cl.direct_send(text, thread_ids=[thread_id])
            return True
        except Exception as e2:
            print(f"   ❌ فشل إرسال النص: {e2}")
            return False

def send_message_with_actions(text: str, actions: list, thread_id: str):
    """
    إرسال رسالة مع إجراءات (طريقة بديلة باستخدام Action Buttons)
    """
    try:
        # بعض إصدارات instagrapi تدعم هذا
        if hasattr(cl, 'direct_send_with_actions'):
            cl.direct_send_with_actions(
                text=text,
                thread_ids=[thread_id],
                actions=actions
            )
        else:
            # الطريقة اليدوية
            msg = text + "\n\n"
            for i, action in enumerate(actions, 1):
                msg += f"{i}. {action['label']}\n"
            msg += "\n📌 اكتب رقم الاختيار"
            cl.direct_send(msg, thread_ids=[thread_id])
        return True
    except Exception as e:
        print(f"   ⚠️ خطأ: {e}")
        try:
            cl.direct_send(text, thread_ids=[thread_id])
            return True
        except:
            return False

# ─── بناء رسائل القائمة مع الأزرار كنص ──────────────────────────────────────

def create_main_menu_text(username: str) -> str:
    """قائمة رئيسية مع أزرار نصية"""
    cfg = load_menu()
    name = cfg["owner"]["name"]
    return (
        f"👋 أهلاً وسهلاً @{username}!\n\n"
        f"أنا {name}، مساعدك الذكي ✨\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **اختر من القائمة:**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣  من أنا؟\n"
        f"2️⃣  مشاريعي 🚀\n"
        f"3️⃣  تواصل معي 📬\n"
        f"4️⃣  اسألني أي شيء 🤖\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✏️ أرسل رقم الاختيار أو اكتب سؤالك مباشرة!"
    )

def create_projects_text() -> str:
    """قائمة المشاريع مع أزرار نصية"""
    cfg = load_menu()
    lines = [
        "🚀 **مشاريعي**",
        "━━━━━━━━━━━━━━━━━━━━"
    ]
    for p in cfg["projects"]:
        lines.append(f"{p['emoji']} {p['id']}. {p['name']}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📌 أرسل رقم المشروع للتفاصيل")
    lines.append("↩️ أو اكتب (رجوع) للقائمة الرئيسية")
    return "\n".join(lines)

def create_about_text() -> str:
    """معلومات شخصية"""
    cfg = load_menu()
    o = cfg["owner"]
    return (
        f"👨‍💻 **{o['name']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 {o['title']}\n\n"
        f"📝 {o['bio']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤲 **دعاء للوالدين:**\n"
        f"{o['dua']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"↩️ اكتب (رجوع) للقائمة الرئيسية"
    )

def create_contact_text() -> str:
    """معلومات التواصل"""
    cfg = load_menu()
    o = cfg["owner"]
    return (
        f"📬 **تواصل مع {o['name']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 **واتساب:**\n{o['whatsapp']}\n\n"
        f"✈️ **تيليغرام:**\n{o['telegram']}\n\n"
        f"🤝 يسعدني التواصل معك!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"↩️ اكتب (رجوع) للقائمة الرئيسية"
    )

def create_ai_welcome_text() -> str:
    """ترحيب الذكاء الاصطناعي"""
    return (
        "🤖 **وضع الدردشة الذكية**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "اطرح سؤالك وسأجيبك فوراً!\n\n"
        "💡 يمكنك طرح أي سؤال في مجال:\n"
        "• البرمجة والتقنية\n"
        "• التعليم والتطوير\n"
        "• المشاريع والأعمال\n\n"
        "↩️ اكتب (رجوع) للقائمة الرئيسية"
    )

def create_project_detail_text(pid: int) -> str:
    """تفاصيل مشروع محدد"""
    cfg = load_menu()
    p = next((x for x in cfg["projects"] if x["id"] == pid), None)
    if not p:
        return "❌ مشروع غير موجود\n↩️ اكتب (مشاريع) للقائمة"
    return (
        f"{p['emoji']} **{p['name']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 **الوصف:**\n{p['description']}\n\n"
        f"🔗 **الرابط:**\n{p['link']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 اكتب (مشاريع) لباقي المشاريع\n"
        f"↩️ أو (رجوع) للقائمة الرئيسية"
    )

# ─── Groq AI ──────────────────────────────────────────────────────────────────
def get_ai_response(message: str, username: str) -> str:
    try:
        cfg = load_menu()
        system = cfg.get("ai_personality", DEFAULT_MENU["ai_personality"])
        model  = cfg.get("groq_model", DEFAULT_MENU["groq_model"])

        completion = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system",  "content": system},
                {"role": "user",    "content": f"@{username}: {message}"}
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ خطأ Groq: {e}")
        return "عذراً، حدث خطأ مؤقت. حاول مرة أخرى 🙏"

# ─── حالة المستخدمين ──────────────────────────────────────────────────────────
users: dict[str, dict] = {}

def get_user(sid: str) -> dict:
    if sid not in users:
        users[sid] = {"state": "main", "last_msg_id": None, "first": True}
    return users[sid]

# ─── معالج الرسائل ────────────────────────────────────────────────────────────

def process(sender_id: str, username: str, text: str, thread_id: str):
    text  = text.strip()
    lower = text.lower()
    u     = get_user(sender_id)

    # ─ رجوع دائماً يعمل
    if lower in {"رجوع", "back", "قائمة", "menu", "رئيسية", "البداية", "ابدا"}:
        u["state"] = "main"
        cl.direct_send(create_main_menu_text(username), thread_ids=[thread_id])
        return

    # ─ اختصارات سريعة
    if lower in {"مشاريع", "projects"}:
        u["state"] = "projects"
        cl.direct_send(create_projects_text(), thread_ids=[thread_id])
        return

    if lower in {"من انت", "من أنت", "من انا", "من أنا", "about"}:
        u["state"] = "about"
        cl.direct_send(create_about_text(), thread_ids=[thread_id])
        return

    if lower in {"تواصل", "contact", "واتساب", "تيليغرام"}:
        u["state"] = "contact"
        cl.direct_send(create_contact_text(), thread_ids=[thread_id])
        return

    # ─ أول رسالة
    if u["first"]:
        u["first"] = False
        u["state"] = "main"
        cl.direct_send(create_main_menu_text(username), thread_ids=[thread_id])
        return

    # ─ القائمة الرئيسية
    if u["state"] == "main":
        if text in ("1", "١"):
            u["state"] = "about"
            cl.direct_send(create_about_text(), thread_ids=[thread_id])
        elif text in ("2", "٢"):
            u["state"] = "projects"
            cl.direct_send(create_projects_text(), thread_ids=[thread_id])
        elif text in ("3", "٣"):
            u["state"] = "contact"
            cl.direct_send(create_contact_text(), thread_ids=[thread_id])
        elif text in ("4", "٤"):
            u["state"] = "ai"
            cl.direct_send(create_ai_welcome_text(), thread_ids=[thread_id])
        else:
            # أي نص حر → ذكاء اصطناعي
            response = get_ai_response(text, username)
            cl.direct_send(
                f"{response}\n\n━━━━━━━━━━━━━━━━━━━━\n↩️ اكتب (رجوع) للقائمة الرئيسية",
                thread_ids=[thread_id]
            )
        return

    # ─ في صفحة المشاريع
    if u["state"] == "projects":
        cfg = load_menu()
        ids = [str(p["id"]) for p in cfg["projects"]]
        if text in ids:
            cl.direct_send(create_project_detail_text(int(text)), thread_ids=[thread_id])
        else:
            # عرض قائمة المشاريع مرة أخرى
            cl.direct_send(create_projects_text(), thread_ids=[thread_id])
        return

    # ─ وضع AI
    if u["state"] == "ai":
        if lower in {"رجوع", "back", "قائمة"}:
            u["state"] = "main"
            cl.direct_send(create_main_menu_text(username), thread_ids=[thread_id])
        else:
            response = get_ai_response(text, username)
            cl.direct_send(
                f"{response}\n\n━━━━━━━━━━━━━━━━━━━━\n↩️ اكتب (رجوع) للقائمة الرئيسية",
                thread_ids=[thread_id]
            )
        return

    # fallback
    u["state"] = "main"
    cl.direct_send(create_main_menu_text(username), thread_ids=[thread_id])

# ─── Polling ──────────────────────────────────────────────────────────────────
def polling_loop():
    n = 0
    while True:
        try:
            n += 1
            print(f"🔍 [{n}] فحص الرسائل...", end=" ", flush=True)
            
            # تحديث الجلسة كل 10 دورات
            if n % 10 == 0:
                try:
                    cl.get_timeline_feed()
                    cl.dump_settings("session.json")
                    print("🔄 تم تحديث الجلسة")
                except:
                    pass
            
            threads = cl.direct_threads(amount=20)
            new = 0

            for thread in threads:
                if not thread.messages:
                    continue
                msg = thread.messages[0]
                sid = str(msg.user_id)

                if sid == str(cl.user_id):
                    continue
                if msg.item_type != "text":
                    continue
                if not msg.text:
                    continue

                mid = str(msg.id)
                u   = get_user(sid)
                if u.get("last_msg_id") == mid:
                    continue

                u["last_msg_id"] = mid
                new += 1

                username = sid
                try:
                    info = cl.user_info(int(sid))
                    username = info.username
                except:
                    pass

                print(f"\n📨 @{username}: {msg.text[:60]}")
                process(sid, username, msg.text, str(thread.id))
                time.sleep(1.5)

            print(f"{'جديد: '+str(new) if new else 'لا جديد'}")
            time.sleep(12)

        except LoginRequired:
            print("\n⚠️ انتهت الجلسة — إعادة تسجيل...")
            login_instagram()
            time.sleep(15)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"\n⚠️ خطأ: {e}")
            time.sleep(20)

# ─── تشغيل ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*55)
    print("  🤖  بوت إنستغرام الذكي | قوائم تفاعلية")
    print("  ⚡  مشغّل بـ Groq + Llama 3.3 70B")
    print("="*55)
    print(f"  👤  الحساب : @{cl.username}")
    print(f"  🌐  لوحة التحكم : http://localhost:5000")
    print("="*55 + "\n")

    try:
        from dashboard import run_dashboard
        t = threading.Thread(target=run_dashboard, daemon=True)
        t.start()
        print("✅ لوحة التحكم تعمل\n")
    except Exception as e:
        print(f"⚠️ لوحة التحكم: {e}\n")

    try:
        polling_loop()
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت.")