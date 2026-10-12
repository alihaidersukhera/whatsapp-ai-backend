"""
WhatsApp AI Platform - Bot Brain
Rule-based demo brain with optional Gemini AI fallback.
All user-facing replies are in Roman Urdu (mixed with light English).
"""
import os
import re

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except Exception:
    _GENAI_AVAILABLE = False


class BotBrain:
    """Handles one conversational turn per user, incl. a COD order flow."""

    def __init__(self, business_name="MuvMod Shoes", owner_whatsapp="03278369194"):
        self.business_name = business_name
        self.owner_whatsapp = owner_whatsapp
        self.sessions = {}          # user_id -> {"state":..., "order": {...}}
        self.conversation_log = []  # demo dashboard log
        self.products = [
            {"id": "1", "name": "Nike Football Shoes (Original Preloved)", "price": 9000},
            {"id": "2", "name": "Ballet Shoes", "price": 1299},
            {"id": "3", "name": "Fancy Slides", "price": 999},
            {"id": "4", "name": "Posh Pumps", "price": 1199},
        ]
        self._gemini_model = None
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if api_key and _GENAI_AVAILABLE:
            try:
                genai.configure(api_key=api_key)
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash")
            except Exception:
                self._gemini_model = None

    # ---------- session helpers ----------
    def _session(self, user_id):
        return self.sessions.setdefault(
            user_id, {"state": "idle", "order": {}}
        )

    def _product_list(self):
        lines = ["🛍️ *Hamari Products:*\n"]
        for p in self.products:
            lines.append(f"{p['id']}. {p['name']} — Rs. {p['price']:,}")
        lines.append("\nOrder karne ke liye likhein: *order*")
        return "\n".join(lines)

    # ---------- main entry ----------
    def handle_message(self, text, user_id="demo-user"):
        text = (text or "").strip()
        low = text.lower()
        sess = self._session(user_id)

        if sess["state"] != "idle":
            reply = self._advance_order(sess, text)
        elif re.search(r"\b(assalam|salam|aoa|hello|hi|hey)\b", low):
            reply = (f"Walaikum Assalam! 👋 *{self.business_name}* me khush aamdeed!\n\n"
                     "Me aapki kese madad kar sakta hun?\n"
                     "• Products dekhne ke liye: *products*\n"
                     "• Order karne ke liye: *order*\n"
                     "• Kisi insan se baat karni ho to: *human*")
        elif "order" in low or "kharid" in low or "buy" in low or "mangwana" in low:
            reply = self._start_order(sess)
        elif "product" in low or "cheez" in low or "shoes" in low or "catalog" in low:
            reply = self._product_list()
        elif any(w in low for w in ["price", "qeemat", "rate", "kimat", "paisay", "paisy"]):
            reply = self._product_list()
        elif any(w in low for w in ["timing", "time", "open", "khula", "band", "hours"]):
            reply = "🕘 Hamari shop timings: *Subah 10 – Raat 9* (haftay ke 7 din khula!)"
        elif any(w in low for w in ["location", "address", "kahan", "pata", "dukkan", "shop kahan"]):
            reply = "📍 Hum online hain — *poore Pakistan me free delivery!* Order WhatsApp par hi ho jayega."
        elif any(w in low for w in ["delivery", "bhijwana", "parsal", "courier", "kitne din"]):
            reply = "🚚 *Free delivery* poore Pakistan me! Order ke 2–4 din me aapke paas. Payment Cash on Delivery (COD) — pehle cheez dekhein, phir paise dein!"
        elif any(w in low for w in ["return", "wapis", "exchange", "badalna"]):
            reply = "🔄 Easy return policy hai! Koi masla ho to 7 din me *exchange* ho jayega. Bas humein WhatsApp par batayein."
        elif any(w in low for w in ["human", "insan", "banda", "owner", "malik", "call", "phone"]):
            reply = (f"🧑‍💼 Bilkul! Hamari team ka banda aapse khud baat karega.\n"
                     f"Aap direct WhatsApp bhi kar sakte hain: *{self.owner_whatsapp}*")
        elif any(w in low for w in ["shukriya", "thanks", "thank"]):
            reply = "Khush aamdeed! 😊 Koi aur madad chahiye to bas likhein."
        elif low in ["bye", "allah hafiz", "khuda hafiz"]:
            reply = f"Allah Hafiz! 👋 *{self.business_name}* ko yaad rakhiye ga!"
        else:
            reply = self._ai_fallback(text)

        self.conversation_log.append(
            {"user_id": user_id, "incoming": text, "reply": reply}
        )
        return reply

    # ---------- order flow ----------
    def _start_order(self, sess):
        sess["state"] = "awaiting_product"
        sess["order"] = {}
        return ("🛒 *Order shuru karte hain!*\n\n" + self._product_list() +
                "\n\nProduct ka *number* likhein (jaise: 2)")

    def _advance_order(self, sess, text):
        low = text.lower()
        state = sess["state"]
        order = sess["order"]

        if any(w in low for w in ["cancel", "khatam", "rehne", "nahi chahiye"]):
            sess["state"] = "idle"
            sess["order"] = {}
            return "Koi baat nahi! Order cancel kar diya. 👍 Dobara order ke liye *order* likhein."

        if state == "awaiting_product":
            prod = next((p for p in self.products if p["id"] == text.strip()), None)
            if not prod:
                return "⚠️ Sahi number likhein (1–4). Ya *cancel* likh kar order rok dein."
            order["product"] = prod
            sess["state"] = "awaiting_name"
            return (f"✅ *{prod['name']}* — Rs. {prod['price']:,}\n\n"
                    "Ab apna *naam* likhein:")

        if state == "awaiting_name":
            if len(text) < 2:
                return "⚠️ Apna naam likhein:"
            order["name"] = text.strip()
            sess["state"] = "awaiting_address"
            return f"Shukriya {order['name']}! 🏠 Ab apna *mukamal address* (sheher ke saath) likhein:"

        if state == "awaiting_address":
            if len(text) < 5:
                return "⚠️ Mukamal address likhein (gali/mohallah + sheher):"
            order["address"] = text.strip()
            sess["state"] = "awaiting_confirm"
            p = order["product"]
            return (f"📝 *Order confirm karein:*\n\n"
                    f"Product: {p['name']}\n"
                    f"Qeemat: Rs. {p['price']:,} (COD)\n"
                    f"Naam: {order['name']}\n"
                    f"Address: {order['address']}\n\n"
                    "Confirm ke liye *haan* likhein, cancel ke liye *cancel*:")

        if state == "awaiting_confirm":
            if low in ["haan", "han", "yes", "confirm", "ok", "theek"]:
                p = order["product"]
                sess["state"] = "idle"
                sess["order"] = {}
                return (f"🎉 *Order confirm ho gaya!*\n\n"
                        f"{p['name']} — Rs. {p['price']:,}\n"
                        "2–4 din me aapke paas pohnch jayega. Payment delivery par (COD).\n\n"
                        f"Shukriya {order['name']}! *{self.business_name}* par bharosa karne ka! ❤️")
            sess["state"] = "idle"
            sess["order"] = {}
            return "Order cancel kar diya. Koi baat nahi! 👍"

        sess["state"] = "idle"
        return self._ai_fallback(text)

    # ---------- AI fallback ----------
    def _ai_fallback(self, text):
        if self._gemini_model:
            try:
                prompt = (f"You are a friendly WhatsApp shop assistant for '{self.business_name}' "
                          f"(shoes store, Pakistan, COD, free delivery). Reply in Roman Urdu, "
                          f"short (under 40 words), warm. Customer asked: {text}")
                resp = self._gemini_model.generate_content(prompt)
                return resp.text.strip()[:400]
            except Exception:
                pass
        return ("Samajh nahi aaya! 😅 Aap ye try karein:\n"
                "• *products* — cheezen dekhein\n"
                "• *order* — order karein\n"
                "• *human* — kisi insan se baat karein")
