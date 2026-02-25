import asyncio
import os
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, FSInputFile
)
from aiogram.filters import CommandStart, Command

# =========================
# TOKEN (DEMO UCHUN)
# =========================
BOT_TOKEN = "8742351117:AAGoizZ2vuK7x7-VMRpOI2slWQL_x9DAepg"   # <-- shu yerga token qo'ying
ADMIN_IDS = {7958070473}             # <-- admin id(lar)

# =========================
# TXT SAQLASH
# =========================
DATA_DIR = "data"
ORDERS_FILE = os.path.join(DATA_DIR, "orders.txt")
os.makedirs(DATA_DIR, exist_ok=True)

def save_order_to_txt(order_text: str):
    with open(ORDERS_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 50 + "\n")
        f.write(f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(order_text + "\n")

# =========================
# DEMO MAHSULOTLAR
# =========================
@dataclass
class Product:
    id: int
    category: str
    name: str
    price: int

CATEGORIES = ["Telefon", "Aksesuar", "Noutbuk"]

PRODUCTS: List[Product] = [
    Product(1, "Telefon", "iPhone 13", 8500000),
    Product(2, "Telefon", "Samsung A54", 4200000),
    Product(3, "Aksesuar", "AirPods", 1500000),
    Product(4, "Noutbuk", "Lenovo ThinkPad", 7800000),
]

# user_id -> {product_id: qty}
CART: Dict[int, Dict[int, int]] = {}

# =========================
# KEYBOARDLAR
# =========================
def kb_categories():
    rows = [[InlineKeyboardButton(text=c, callback_data=f"cat:{c}")] for c in CATEGORIES]
    rows.append([InlineKeyboardButton(text="🛒 Savat", callback_data="cart:show")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_products(category: str):
    rows = []
    for p in PRODUCTS:
        if p.category == category:
            rows.append([InlineKeyboardButton(
                text=f"{p.name} — {p.price:,} so'm",
                callback_data=f"prod:{p.id}"
            )])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="home")])
    rows.append([InlineKeyboardButton(text="🛒 Savat", callback_data="cart:show")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_product_actions(pid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Savatga qo‘shish", callback_data=f"cart:add:{pid}")],
        [InlineKeyboardButton(text="🛒 Savat", callback_data="cart:show")],
        [InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="home")]
    ])

def kb_cart():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="order:start")],
        [InlineKeyboardButton(text="🧹 Tozalash", callback_data="cart:clear")],
        [InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="home")]
    ])

def contact_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )

# =========================
# YORDAMCHI FUNKSIYALAR
# =========================
def cart_total(user_id: int) -> int:
    total = 0
    for pid, qty in CART.get(user_id, {}).items():
        p = next((x for x in PRODUCTS if x.id == pid), None)
        if p:
            total += p.price * qty
    return total

def cart_text(user_id: int) -> str:
    items = CART.get(user_id, {})
    if not items:
        return "🛒 Savatingiz bo‘sh."
    lines = ["🛒 Savat:"]
    for pid, qty in items.items():
        p = next((x for x in PRODUCTS if x.id == pid), None)
        if p:
            lines.append(f"- {p.name} x{qty} = {(p.price * qty):,} so'm")
    lines.append(f"\nJami: {cart_total(user_id):,} so'm")
    return "\n".join(lines)

# =========================
# BOT
# =========================
async def main():
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN qo‘yilmagan. BOT_TOKEN ni bot.py ichida to‘ldiring.")

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    # START
    @dp.message(CommandStart())
    async def start(m: Message):
        await m.answer("🛍 Online Shop Bot\nKategoriyani tanlang:", reply_markup=kb_categories())

    # HOME
    @dp.callback_query(F.data == "home")
    async def home(c: CallbackQuery):
        await c.message.edit_text("Kategoriyani tanlang:", reply_markup=kb_categories())
        await c.answer()

    # CATEGORY -> PRODUCTS
    @dp.callback_query(F.data.startswith("cat:"))
    async def open_category(c: CallbackQuery):
        category = c.data.split(":", 1)[1]
        await c.message.edit_text(f"📦 {category} mahsulotlari:", reply_markup=kb_products(category))
        await c.answer()

    # PRODUCT DETAIL
    @dp.callback_query(F.data.startswith("prod:"))
    async def open_product(c: CallbackQuery):
        pid = int(c.data.split(":", 1)[1])
        p = next((x for x in PRODUCTS if x.id == pid), None)
        if not p:
            await c.answer("Mahsulot topilmadi", show_alert=True)
            return
        await c.message.edit_text(
            f"🛒 {p.name}\nNarx: {p.price:,} so'm\n\nSavatga qo‘shasizmi?",
            reply_markup=kb_product_actions(pid)
        )
        await c.answer()

    # CART ADD
    @dp.callback_query(F.data.startswith("cart:add:"))
    async def add_cart(c: CallbackQuery):
        pid = int(c.data.split(":")[2])
        CART.setdefault(c.from_user.id, {})
        CART[c.from_user.id][pid] = CART[c.from_user.id].get(pid, 0) + 1
        await c.message.edit_text(cart_text(c.from_user.id), reply_markup=kb_cart())
        await c.answer("✅ Qo‘shildi")

    # CART SHOW
    @dp.callback_query(F.data == "cart:show")
    async def show_cart(c: CallbackQuery):
        await c.message.edit_text(cart_text(c.from_user.id), reply_markup=kb_cart())
        await c.answer()

    # CART CLEAR
    @dp.callback_query(F.data == "cart:clear")
    async def clear_cart(c: CallbackQuery):
        CART[c.from_user.id] = {}
        await c.message.edit_text("🧹 Savat tozalandi.", reply_markup=kb_categories())
        await c.answer()

    # ORDER START
    @dp.callback_query(F.data == "order:start")
    async def order_start(c: CallbackQuery):
        if not CART.get(c.from_user.id):
            await c.answer("Savat bo‘sh.", show_alert=True)
            return
        await c.message.answer("📞 Telefon raqamingizni yuboring:", reply_markup=contact_kb())
        await c.answer()

    # CANCEL (matn orqali)
    @dp.message(F.text == "❌ Bekor qilish")
    async def cancel_flow(m: Message):
        m.bot_data.pop("phone", None)
        await m.answer("Bekor qilindi. Kategoriyani tanlang:", reply_markup=kb_categories())

    # RECEIVE CONTACT  ✅ (SIZ SO'RAGAN XABAR SHU YERDA)
    @dp.message(F.contact)
    async def get_contact(m: Message):
        if not CART.get(m.from_user.id):
            await m.answer("🛒 Savatingiz bo‘sh. Avval mahsulot tanlang.", reply_markup=kb_categories())
            return

        m.bot_data["phone"] = m.contact.phone_number
        await m.answer(
            "📞 Raqamingiz qabul qilindi ✅\n"
            "📍 Endi manzilingizni yozing (masalan: Chilonzor, 5-mavze, 12-uy):",
            reply_markup=cancel_kb()
        )

    # RECEIVE ADDRESS -> COMPLETE ORDER ✅ (SIZ SO'RAGAN “ALOQAGA CHIQAMIZ” XABARI)
    @dp.message(F.text)
    async def get_address(m: Message):
        if "phone" in m.bot_data and CART.get(m.from_user.id):
            phone = m.bot_data.pop("phone")
            address = m.text.strip()

            summary = (
                "🆕 Yangi buyurtma!\n\n"
                f"{cart_text(m.from_user.id)}\n\n"
                f"📞 Tel: {phone}\n"
                f"📍 Manzil: {address}\n"
                f"👤 User: @{m.from_user.username or 'yo‘q'} (ID: {m.from_user.id})"
            )

            save_order_to_txt(summary)

            for admin in ADMIN_IDS:
                try:
                    await bot.send_message(admin, summary)
                except Exception:
                    pass

            CART[m.from_user.id] = {}
            await m.answer(
                "✅ Buyurtmangiz qabul qilindi!\nTez orada siz bilan bog‘lanamiz 😊",
                reply_markup=kb_categories()
            )
        else:
            # oddiy matn yozsa ham yo'naltiramiz
            await m.answer("Kategoriyadan mahsulot tanlang:", reply_markup=kb_categories())

    # ADMIN: orders.txt yuborish
    @dp.message(Command("orders"))
    async def send_orders(m: Message):
        if m.from_user.id not in ADMIN_IDS:
            return
        if not os.path.exists(ORDERS_FILE):
            await m.answer("Hali buyurtmalar yo‘q.")
            return
        await m.answer_document(FSInputFile(ORDERS_FILE), caption="📄 orders.txt")

    print("Bot ishlayapti...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())