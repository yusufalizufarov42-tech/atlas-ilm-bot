import os
import asyncio
from typing import Union
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

# 1. BotFather bergan token — Render'ning Environment bo'limidagi
#    BOT_TOKEN o'zgaruvchisidan o'qiladi (kodga yozilmaydi).
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN muhit o'zgaruvchisi sozlanmagan! Render dashboard -> Environment bo'limiga qo'shing.")

# 2. Kanalingiz username'i
CHANNEL_ID = "@atlas_ilm"

# 3. Node.js backend manzili (server.js shu yerda ishlaydi) va ichki himoya kaliti
#    (INTERNAL_API_KEY — server.js'dagi bilan BIR XIL bo'lishi kerak, Render Environment'da sozlanadi)
BACKEND_URL = os.environ.get("BACKEND_URL", "https://atlas-nickname-backend.onrender.com")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY")  # ixtiyoriy, lekin tavsiya etiladi

# 4. Mini App havolalari — MAIN_APP_URL'ni o'zingizning haqiqiy manzilingizga almashtiring!
MAIN_APP_URL = "https://yusufalizufarov42-tech.github.io/atlas-mini-app/"
TESTS_URL = "https://atlas-nickname-backend.onrender.com/tests"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================== O'ZBEKISTON VILOYAT/TUMANLARI ==================
# index.html'dagi UZ_REGIONS bilan bir xil ro'yxat — nomlar bir joyda ikki xil bo'lib qolmasin.
UZ_REGIONS = {
    "Andijon viloyati": ["Andijon shahri","Andijon tumani","Asaka","Baliqchi","Bo'z","Buloqboshi","Izboskan","Jalaquduq","Xo'jaobod","Marhamat","Oltinko'l","Paxtaobod","Qo'rg'ontepa","Shahrixon","Ulug'nor","Xonobod"],
    "Buxoro viloyati": ["Buxoro shahri","Buxoro tumani","G'ijduvon","Jondor","Kogon","Qorako'l","Qorovulbozor","Peshku","Romitan","Shofirkon","Vobkent","Olot"],
    "Farg'ona viloyati": ["Farg'ona shahri","Marg'ilon","Qo'qon","Farg'ona tumani","Bag'dod","Beshariq","Buvayda","Dang'ara","Furqat","Oltiariq","Qo'shtepa","Rishton","So'x","Toshloq","Uchko'prik","O'zbekiston tumani","Yozyovon","Uchkuduq"],
    "Jizzax viloyati": ["Jizzax shahri","Arnasoy","Baxmal","Do'stlik","Forish","G'allaorol","Sharof Rashidov","Yangiobod","Mirzachoʻl","Paxtakor","Zafarobod","Zarbdor","Zomin"],
    "Namangan viloyati": ["Namangan shahri","Chortoq","Chust","Kosonsoy","Mingbuloq","Namangan tumani","Norin","Pop","To'raqo'rg'on","Uychi","Uchqo'rg'on","Yangiqo'rg'on"],
    "Navoiy viloyati": ["Navoiy shahri","Zarafshon","Karmana","Konimex","Qiziltepa","Xatirchi","Navbahor","Nurota","Tomdi","Uchquduq"],
    "Qashqadaryo viloyati": ["Qarshi shahri","Kasbi","Kitob","Koson","Qamashi","Qarshi tumani","Muborak","Nishon","Chiroqchi","Shahrisabz","Dehqonobod","G'uzor","Mirishkor","Yakkabog'"],
    "Qoraqalpog'iston Respublikasi": ["Nukus shahri","Amudaryo","Beruniy","Chimboy","Ellikqal'a","Kegeyli","Mo'ynoq","Nukus tumani","Qanliko'l","Qorao'zak","Qo'ng'irot","Shumanay","Taxtako'pir","To'rtko'l","Xo'jayli"],
    "Samarqand viloyati": ["Samarqand shahri","Bulung'ur","Ishtixon","Jomboy","Kattaqo'rg'on","Qo'shrabot","Narpay","Nurobod","Oqdaryo","Payariq","Pastdarg'om","Paxtachi","Samarqand tumani","Toyloq","Urgut"],
    "Sirdaryo viloyati": ["Guliston shahri","Boyovut","Guliston tumani","Mirzaobod","Oqoltin","Sardoba","Sayxunobod","Sirdaryo","Xovos","Yangiyer"],
    "Surxondaryo viloyati": ["Termiz shahri","Angor","Bandixon","Boysun","Denov","Jarqo'rg'on","Muzrabot","Oltinsoy","Qiziriq","Qumqo'rg'on","Sariosiyo","Sherobod","Shurchi","Termiz tumani","Uzun"],
    "Toshkent shahri": ["Bektemir","Chilonzor","Mirobod","Mirzo Ulug'bek","Olmazor","Sergeli","Shayxontohur","Uchtepa","Yakkasaroy","Yashnobod","Yunusobod","Yangihayot"],
    "Toshkent viloyati": ["Angren","Bekobod","Chirchiq","Nurafshon","Oxangaron","Yangiyo'l","Bo'ka","Bo'stonliq","Chinoz","Qibray","Ohangaron tumani","Parkent","Piskent","Quyichirchiq","Yuqorichirchiq","O'rtachirchiq","Zangiota"],
    "Xorazm viloyati": ["Urganch shahri","Bog'ot","Gurlan","Xazorasp","Xiva","Xonqa","Qo'shko'pir","Shovot","Urganch tumani","Yangiariq","Yangibozor"],
}
REGION_NAMES = list(UZ_REGIONS.keys())  # "reg:<index>" callback_data uchun

def chunk_buttons(buttons, per_row=2):
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]

# ================== FSM HOLATLARI ==================
class Reg(StatesGroup):
    name = State()
    contact = State()
    region = State()
    district = State()

# ================== OBUNA TEKSHIRUVI (avvalgi kod, o'zgarmagan) ==================
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="check_subscription")]
    ])

# ================== BACKEND BILAN ALOQA ==================
async def fetch_profile(user_id: int) -> Union[dict, None]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/profile",
                json={"userId": str(user_id)},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                return data if data.get("success") else None
    except Exception as e:
        print("[bot] /api/profile xatosi:", e)
        return None

async def push_details(user_id: int, full_name: str, phone: str, region: str, district: str) -> bool:
    headers = {"X-Internal-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/set-details",
                json={"userId": str(user_id), "fullName": full_name, "phone": phone, "region": region, "district": district},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                return bool(data.get("success"))
    except Exception as e:
        print("[bot] /api/set-details xatosi:", e)
        return False

# ================== XUSH KELIBSIZ XABARI (ro'yxatdan o'tgandan keyin) ==================
def welcome_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Mini App", web_app=WebAppInfo(url=MAIN_APP_URL))],
        [InlineKeyboardButton(text="📝 Testlar bo'limi", web_app=WebAppInfo(url=TESTS_URL))],
        [InlineKeyboardButton(text="✏️ Ma'lumotlarni o'zgartirish", callback_data="edit_details")],
    ])

async def send_welcome(message_or_callback):
    text = "Xush kelibsiz! Quyidagilardan birini tanlang:"
    kb = welcome_keyboard()
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.answer(text, reply_markup=kb)
    else:
        await message_or_callback.answer(text, reply_markup=kb)

# ================== RO'YXATDAN O'TISH OQIMINI BOSHLASH ==================
async def start_registration(message: types.Message, state: FSMContext):
    await state.set_state(Reg.name)
    await message.answer(
        "Ismingiz va familiyangizni to'liq kiriting (masalan: Aliyev Vali):",
        reply_markup=ReplyKeyboardRemove()
    )

async def proceed_after_subscription(message_or_callback: Union[types.Message, types.CallbackQuery], state: FSMContext):
    user_id = message_or_callback.from_user.id
    profile = await fetch_profile(user_id)
    target_message = message_or_callback.message if isinstance(message_or_callback, types.CallbackQuery) else message_or_callback

    if profile and profile.get("hasDetails"):
        # Ma'lumotlar allaqachon bor — qayta so'ralmaydi, to'g'ridan-to'g'ri xush kelibsiz
        await send_welcome(message_or_callback)
    else:
        await start_registration(target_message, state)

# ================== /start ==================
@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    if await is_subscribed(message.from_user.id):
        await proceed_after_subscription(message, state)
    else:
        await message.answer(
            "Botdan foydalanish uchun avval kanalimizga a'zo bo'ling:",
            reply_markup=get_sub_keyboard()
        )

@dp.callback_query(F.data == "check_subscription")
async def check_callback(callback: types.CallbackQuery, state: FSMContext):
    if await is_subscribed(callback.from_user.id):
        await callback.message.delete()
        await proceed_after_subscription(callback, state)
    else:
        await callback.answer("Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)

# ================== ISM-FAMILIYA ==================
@dp.message(Reg.name)
async def reg_name_handler(message: types.Message, state: FSMContext):
    full_name = (message.text or "").strip()
    if len(full_name) < 3 or len(full_name) > 60 or any(ch.isdigit() for ch in full_name):
        await message.answer("Iltimos, ism-familiyangizni to'g'ri kiriting (faqat harflar, kamida 3 ta belgi).")
        return
    await state.update_data(full_name=full_name)
    await state.set_state(Reg.contact)
    contact_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Rahmat! Endi telefon raqamingizni ulashing:", reply_markup=contact_kb)

# ================== KONTAKT (telefon) ==================
@dp.message(Reg.contact, F.contact)
async def reg_contact_handler(message: types.Message, state: FSMContext):
    if message.contact.user_id != message.from_user.id:
        await message.answer("Iltimos, FAQAT o'zingizning kontaktingizni yuboring.")
        return
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(Reg.region)

    region_buttons = [InlineKeyboardButton(text=name, callback_data=f"reg:{i}") for i, name in enumerate(REGION_NAMES)]
    await message.answer("Viloyatingizni tanlang:", reply_markup=ReplyKeyboardRemove())
    await message.answer("👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=chunk_buttons(region_buttons)))
@dp.message(Reg.contact)
async def reg_contact_fallback(message: types.Message):
    await message.answer("Iltimos, pastdagi «📞 Kontaktni yuborish» tugmasini bosing.")

# ================== VILOYAT ==================
@dp.callback_query(Reg.region, F.data.startswith("reg:"))
async def reg_region_handler(callback: types.CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    region_name = REGION_NAMES[idx]
    districts = UZ_REGIONS[region_name]
    await state.update_data(region=region_name)
    await state.set_state(Reg.district)

    kb_rows = [InlineKeyboardButton(text=d, callback_data=f"dist:{i}") for i, d in enumerate(districts)]
    await callback.message.edit_text(
        f"Viloyat: {region_name}\n\nEndi tuman/shaharni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=chunk_buttons(kb_rows))
    )
    await callback.answer()

# ================== TUMAN — YAKUNIY QADAM ==================
@dp.callback_query(Reg.district, F.data.startswith("dist:"))
async def reg_district_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    region_name = data.get("region")
    districts = UZ_REGIONS.get(region_name, [])
    idx = int(callback.data.split(":")[1])
    if idx >= len(districts):
        await callback.answer("Xatolik, qayta urinib ko'ring.", show_alert=True)
        return
    district_name = districts[idx]

    full_name = data.get("full_name")
    phone = data.get("phone")
    ok = await push_details(callback.from_user.id, full_name, phone, region_name, district_name)
    await state.clear()

    if ok:
        await callback.message.edit_text(f"✅ Ma'lumotlaringiz saqlandi!\n\n{full_name}\n{region_name}, {district_name}")
        await send_welcome(callback)
    else:
        await callback.message.edit_text("❌ Saqlashda xatolik yuz berdi. Iltimos, /start bosib qayta urinib ko'ring.")
    await callback.answer()

# ================== MA'LUMOTLARNI O'ZGARTIRISH ==================
@dp.callback_query(F.data == "edit_details")
async def edit_details_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_registration(callback.message, state)

@dp.message(Command("profil"))
async def profil_command(message: types.Message, state: FSMContext):
    await start_registration(message, state)

# ================== RENDER UCHUN OYNA TIRIK EKANLIGINI KO'RSATISH ==================
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def main():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
