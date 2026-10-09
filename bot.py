import os
import re
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
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineQueryResultArticle, InputTextMessageContent
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

# 5. Mini App'ni boshqa chat/guruhlarda ochish uchun to'g'ridan-to'g'ri havola (inline rejim va /ilova shundan foydalanadi).
#    BotFather'da asosiy Mini App sozlangan bo'lishi kerak (Bot Settings -> Configure Mini App), yoki /newapp bilan
#    qisqa nom berib, MINI_APP_SHORT_NAME o'zgaruvchisiga yozing.
BOT_USERNAME = os.environ.get("BOT_USERNAME", "atlasilmbot").lstrip("@")
MINI_APP_SHORT_NAME = os.environ.get("MINI_APP_SHORT_NAME", "").strip()

def mini_link(param: str = "app") -> str:
    base = f"https://t.me/{BOT_USERNAME}" + (f"/{MINI_APP_SHORT_NAME}" if MINI_APP_SHORT_NAME else "")
    return f"{base}?startapp={param}"

def link_kb(text: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, url=url)]])

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

GUIDE_TEXT = """📖 <b>Atlas Ilm botidan qanday foydalanish</b>

<b>1️⃣ Ro'yxatdan o'tish</b>
Botga birinchi marta kirganda:
• Avval @atlas_ilm kanaliga obuna bo'lishingiz so'raladi (majburiy)
• Ism-familiyangizni yozasiz
• "📞 Kontaktni yuborish" tugmasi orqali telefon raqamingizni ulashasiz
• Viloyat, so'ng tuman/shaharingizni tugmalardan tanlaysiz
Shundan keyin bu ma'lumotlar qayta so'ralmaydi — faqat bir marta.

<b>2️⃣ 📚 Mini App</b>
Asosiy ilova — kimyo va biologiya (6–10-sinf) bo'yicha:
• Mavzuli testlar va mashqlar
• Boshqa o'quvchilar bilan jonli musobaqa (1 kishilik, botga qarshi, onlayn)
• Har bir to'g'ri javob uchun <b>atom</b> yig'asiz
• Yig'ilgan atomlarga do'kondan fayl/materiallarni ochib olishingiz mumkin
• Reyting jadvali — kim ko'proq atom yig'ganini ko'rasiz

<b>👤 Profil bo'limi</b> (Mini App ichida):
• <b>Nickname</b> — xohlasangiz o'zingizga nom qo'yasiz, reytingda shu nom bilan ko'rinasiz (parol bilan birga — parolni unutmang, boshqa qurilmada kirish uchun kerak bo'ladi)
• <b>Eski hisobni bog'lash</b> — agar avval boshqa nickname/parol bilan ro'yxatdan o'tgan bo'lsangiz, shu yerdan kiritib, eski atomlaringizni joriy profilingizga qo'shib olasiz
• <b>Referal havolasi</b> — do'stlaringizni shu havola orqali taklif qilsangiz, har bir qo'shilgan do'st uchun bonus atom olasiz

<b>3️⃣ 📝 Testlar bo'limi</b>
Bu — alohida, chinakam imtihon simulyatori. Ikki turi bor:
• <b>Rasch mock (43 savol)</b> — 1–32 (4 variantli), 33–35 (6 variantli), 36–43 (o'zingiz javob yozasiz). Natija Milliy Sertifikatdagi kabi Rasch modeli bilan hisoblanadi (A+, A, B+... darajalar)
• <b>Javobli test</b> — 30/50/90/100 savoldan iborat, faqat to'g'ri/noto'g'ri bo'yicha baholanadi

<b>Har kim test yarata oladi:</b>
• Savollar faylini (PDF/rasm) yuklaysiz, to'g'ri javoblarni belgilaysiz
• Test kodi beriladi (masalan T-1234)
• Kodni ishtirokchilarga tarqatasiz — ular kodni kiritib testni belgilangan vaqt ichida yechadi
• Test yakunlangach, natijalar jadvali (reyting, ball, daraja) PDF holida sizga (yaratuvchiga) botda yuboriladi
• Kuniga bitta odam cheklangan sondagi test yarata oladi (adolat uchun)

<b>4️⃣ ✏️ Ma'lumotlarni o'zgartirish</b>
Ism, telefon, viloyat, tumaningizni keyinchalik ham xohlagan vaqt qayta kiritib o'zgartirishingiz mumkin. Buyruq: /profil

<b>5️⃣ 🆘 Yordam kerakmi?</b>
/yordam buyrug'ini yuboring, xabaringizni yozing — to'g'ridan-to'g'ri administratorga yetadi.

<b>📋 Foydali buyruqlar:</b>
/start — botni qayta ishga tushirish
/profil — ism/telefon/viloyat/tumanni o'zgartirish
/yordam — administratorga xabar/savol yuborish"""

def chunk_buttons(buttons, per_row=2):
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]

# ================== FSM HOLATLARI ==================
class Reg(StatesGroup):
    name = State()
    contact = State()
    region = State()
    district = State()

class Help(StatesGroup):
    waiting_message = State()

class Quiz(StatesGroup):
    waiting = State()    # admin viktorina matnini yuborishini kutamiz
    confirm = State()    # tasdiqlashni kutamiz

class Broadcast(StatesGroup):
    waiting_text = State()   # admin xabarni yuborishini kutamiz (har qanday turdagi)
    confirm = State()        # admin tasdiqlashini kutamiz

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
    """None — server javob bermadi (uxlab qolgan/ishlamayapti). Bepul hosting uyg'onishi uchun 3 marta urinamiz."""
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BACKEND_URL}/api/profile",
                    json={"userId": str(user_id)},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status >= 500:
                        raise RuntimeError(f"server {resp.status}")
                    data = await resp.json()
                    return data if data.get("success") else None
        except Exception as e:
            print(f"[bot] /api/profile {attempt + 1}-urinish xatosi:", e)
            await asyncio.sleep(3)
    return None

async def push_details(user_id: int, full_name: str, phone: str, region: str, district: str) -> str:
    """Muvaffaqiyatli bo'lsa "" (bo'sh), aks holda sababini qaytaradi."""
    headers = {"X-Internal-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/set-details",
                json={"userId": str(user_id), "fullName": full_name, "phone": phone, "region": region, "district": district},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    return f"server javobi {resp.status}"
                if data.get("success"):
                    return ""
                return str(data.get("error") or f"server javobi {resp.status}")
    except asyncio.TimeoutError:
        return "server javob bermadi (uxlab qolgan bo'lishi mumkin)"
    except Exception as e:
        print("[bot] /api/set-details xatosi:", e)
        return "serverga ulanib bo'lmadi"

async def get_admin_target_id() -> Union[str, None]:
    headers = {"X-Internal-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/admin/target-id",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                return data.get("adminUserId") if data.get("success") else None
    except Exception as e:
        print("[bot] /api/admin/target-id xatosi:", e)
        return None

async def send_broadcast_copy(admin_user_id: int, from_chat_id: int, message_id: int) -> Union[dict, None]:
    """Backend'ga: shu xabarni (har qanday turdagi) hammaga nusxalab yubor. INTERNAL_API_KEY majburiy."""
    headers = {"X-Internal-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/api/admin/broadcast-copy",
                headers=headers,
                json={"adminUserId": str(admin_user_id), "fromChatId": str(from_chat_id), "messageId": message_id},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                return await resp.json()
    except Exception as e:
        print("[bot] /api/admin/broadcast-copy xatosi:", e)
        return None

# ================== XUSH KELIBSIZ XABARI (ro'yxatdan o'tgandan keyin) ==================
def welcome_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Mini App", web_app=WebAppInfo(url=MAIN_APP_URL))],
        [InlineKeyboardButton(text="📝 Testlar bo'limi", web_app=WebAppInfo(url=TESTS_URL))],
        [InlineKeyboardButton(text="✏️ Ma'lumotlarni o'zgartirish", callback_data="edit_details")],
        [InlineKeyboardButton(text="📖 Qo'llanma", callback_data="show_guide")],
        [InlineKeyboardButton(text="📤 Guruhga / do'stga ulashish", switch_inline_query="")],
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
        "Ismingiz va familiyangizni to'liq kiriting — AVVAL ism, keyin familiya (masalan: Vali Aliyev):",
        reply_markup=ReplyKeyboardRemove()
    )

async def proceed_after_subscription(message_or_callback: Union[types.Message, types.CallbackQuery], state: FSMContext):
    user_id = message_or_callback.from_user.id
    profile = await fetch_profile(user_id)
    target_message = message_or_callback.message if isinstance(message_or_callback, types.CallbackQuery) else message_or_callback

    if profile is None:
        # Server javob bermayapti — ro'yxatdan o'tishni boshidan boshlamaymiz (baribir saqlab bo'lmaydi)
        await target_message.answer("⏳ Server hozir javob bermayapti (uxlab qolgan bo'lishi mumkin). 1 daqiqadan so'ng /start ni qayta bosing.")
        return
    if profile.get("hasDetails"):
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
    push_err = await push_details(callback.from_user.id, full_name, phone, region_name, district_name)
    await state.clear()

    if not push_err:
        await callback.message.edit_text(f"✅ Ma'lumotlaringiz saqlandi!\n\n{full_name}\n{region_name}, {district_name}")
        await send_welcome(callback)
    else:
        hint = " (bot va server INTERNAL_API_KEY qiymatlari bir xil emas)" if "Ruxsat" in push_err else ""
        await callback.message.edit_text(f"❌ Saqlashda xatolik: {push_err}{hint}.\nBirozdan so'ng /start bosib qayta urinib ko'ring.")
    await callback.answer()

# ================== MA'LUMOTLARNI O'ZGARTIRISH ==================
@dp.callback_query(F.data == "edit_details")
async def edit_details_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_registration(callback.message, state)

@dp.callback_query(F.data == "show_guide")
async def show_guide_callback(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(GUIDE_TEXT, parse_mode="HTML")

@dp.message(Command("profil"))
async def profil_command(message: types.Message, state: FSMContext):
    await start_registration(message, state)

@dp.message(Command("qollanma"))
async def qollanma_command(message: types.Message):
    await message.answer(GUIDE_TEXT, parse_mode="HTML")

# ================== YORDAM / FIKR-MULOHAZA ==================
@dp.message(Command("yordam"))
async def yordam_command(message: types.Message, state: FSMContext):
    await state.set_state(Help.waiting_message)
    await message.answer("Xabaringizni yozing — u to'g'ridan-to'g'ri administratorga yuboriladi:")

SUPPORT_ID_RE = re.compile(r"🆔\s*(\d{5,})")
SUPPORT_FOOTER = "\n\n↩️ Javob berish uchun shu xabarga Reply qiling."

def support_header(sender: types.User) -> str:
    uname = f" (@{sender.username})" if sender.username else ""
    return f"📩 Yordam so'rovi\n👤 {sender.full_name}{uname}\n🆔 {sender.id}\n"

@dp.message(Help.waiting_message)
async def yordam_receive(message: types.Message, state: FSMContext):
    await state.clear()
    admin_id = await get_admin_target_id()
    if not admin_id:
        await message.answer("❌ Kechirasiz, hozir yubora olmadik (server javob bermadi yoki admin topilmadi). Birozdan so'ng qayta urinib ko'ring.")
        return
    header = support_header(message.from_user)
    try:
        if message.text:
            await bot.send_message(admin_id, f"{header}\n{message.text}{SUPPORT_FOOTER}")
        else:  # rasm, video, fayl, ovozli xabar...
            caption = (header + ("\n" + message.caption if message.caption else "") + SUPPORT_FOOTER)[:1024]
            try:
                await bot.copy_message(chat_id=admin_id, from_chat_id=message.chat.id, message_id=message.message_id, caption=caption)
            except Exception:
                await bot.send_message(admin_id, header + "\n(media xabar)" + SUPPORT_FOOTER)
                await bot.copy_message(chat_id=admin_id, from_chat_id=message.chat.id, message_id=message.message_id)
        await message.answer("✅ Xabaringiz yuborildi. Tez orada javob berishadi.")
    except Exception as e:
        print("[bot] /yordam yuborishda xato:", e)
        await message.answer("❌ Xabar yuborilmadi. Birozdan so'ng qayta urinib ko'ring.")

def support_reply_target(m: types.Message):
    """Admin 'Yordam so'rovi' xabariga Reply qilgan bo'lsa — foydalanuvchi ID'si, aks holda None."""
    r = m.reply_to_message
    if not r or not r.from_user or not r.from_user.is_bot:
        return None
    t = r.text or r.caption or ""
    if "Yordam so'rovi" not in t:
        return None
    mm = SUPPORT_ID_RE.search(t) or re.search(r"\(id:\s*(\d+)\)", t)
    return int(mm.group(1)) if mm else None

# Admin so'rov xabariga Reply qilsa — javob o'sha foydalanuvchiga boradi (matn, rasm, fayl — hammasi)
@dp.message(lambda m: support_reply_target(m) is not None)
async def admin_support_reply(message: types.Message):
    if not await admin_gate(message):
        return
    uid = support_reply_target(message)
    try:
        if message.text:
            await bot.send_message(uid, f"💬 Administrator javobi:\n\n{message.text}")
        else:
            await bot.send_message(uid, "💬 Administrator javobi:")
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
        await message.answer("✅ Javob foydalanuvchiga yuborildi.")
    except Exception as e:
        print("[bot] admin javobi yuborilmadi:", e)
        await message.answer("❌ Yuborib bo'lmadi (foydalanuvchi botni bloklagan yoki ishga tushirmagan bo'lishi mumkin).")

# ================== INLINE REJIM: Mini App'ni istalgan chat/guruhda ulashish ==================
# BotFather: /setinline -> botni tanlang -> matn yozing (masalan "Atlas Ilm"). Keyin istalgan chatda @bot yozilsa, natijalar chiqadi.
INLINE_CODE_RE = re.compile(r"^[A-Za-z0-9]{4,8}$")

@dp.inline_query()
async def inline_handler(q: types.InlineQuery):
    query = (q.query or "").strip()
    results = []
    is_code = bool(INLINE_CODE_RE.match(query))
    if is_code:
        code = query.upper()
        results.append(InlineQueryResultArticle(
            id=f"olimp-{code}", title=f"🏆 Olimpiadaga qo'shilish: {code}",
            description="Tugma bosilganda Mini App'da shu olimpiada ochiladi",
            input_message_content=InputTextMessageContent(message_text=f"🏆 Atlas Ilm olimpiadasi\nKod: {code}\n\nQatnashish uchun tugmani bosing 👇"),
            reply_markup=link_kb("🏆 Olimpiadaga kirish", mini_link(f"olimp_{code}"))))
    results.append(InlineQueryResultArticle(
        id="app", title="🧪 Atlas Ilm Mini App", description="Kimyo va biologiya mashqlari, olimpiadalar, reyting",
        input_message_content=InputTextMessageContent(message_text="🧪 Atlas Ilm — kimyo va biologiya (6–10-sinf) mashqlari, olimpiadalar va reyting.\n\nOchish uchun tugmani bosing 👇"),
        reply_markup=link_kb("🚀 Mini Appni ochish", mini_link("app"))))
    results.append(InlineQueryResultArticle(
        id="olimpiadalar", title="🏆 Olimpiadalar", description="Ochiq olimpiadalar ro'yxatini ochish",
        input_message_content=InputTextMessageContent(message_text="🏆 Atlas Ilm olimpiadalari — qatnashing va natijangizni sinang!\n\nTugmani bosing 👇"),
        reply_markup=link_kb("🏆 Olimpiadalarni ko'rish", mini_link("olimpiadalar"))))
    await q.answer(results, cache_time=30 if is_code else 300, is_personal=False)

# Guruhlarda ham ishlaydi: /ilova
@dp.message(Command("ilova"))
async def ilova_command(message: types.Message):
    await message.answer("🧪 Atlas Ilm — kimyo va biologiya mashqlari, olimpiadalar va reyting.\nOchish uchun tugmani bosing 👇",
                         reply_markup=link_kb("🚀 Mini Appni ochish", mini_link("app")))

# ================== ADMIN: HAMMAGA XABAR (BROADCAST) ==================
# /xabar (yoki eski /savol) — admin matn, rasm, video, fayl yoki post yuboradi,
# bot avval ko'rsatadi, tasdiqlansa hamma foydalanuvchiga nusxalab yuboradi.
async def check_admin(user_id: int):
    """True — admin, False — admin emas, None — server javob bermadi (masalan, Render uxlab qolgan).
    Bepul hosting uyg'onishi 30–60 soniya olishi mumkin, shuning uchun 3 marta urinamiz."""
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{BACKEND_URL}/api/profile", json={"userId": str(user_id)},
                                        timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status >= 500:
                        raise RuntimeError(f"server {resp.status}")
                    data = await resp.json()
                    return bool(data.get("success") and data.get("isAdmin"))
        except Exception as e:
            print(f"[bot] admin tekshiruvi {attempt + 1}-urinish xatosi:", e)
            await asyncio.sleep(3)
    return None

async def is_admin_user(user_id: int) -> bool:
    return (await check_admin(user_id)) is True

async def admin_gate(message: types.Message) -> bool:
    """Admin buyruqlari uchun: ruxsat bo'lsa True; bo'lmasa sababini aniq aytadi."""
    st = await check_admin(message.from_user.id)
    if st:
        return True
    if st is None:
        await message.answer("⏳ Server hozir uyg'onyapti (bepul hosting uxlab qolgan). 1 daqiqadan so'ng buyruqni qayta yozing.")
    else:
        await message.answer(f"Bu buyruq faqat administrator uchun.\nSizning ID: {message.from_user.id} — tekshirish uchun /id yozing.")
    return False

async def backend_status() -> list:
    """Bot -> server aloqasini tekshiradi. Hech qanday maxfiy ma'lumot ko'rsatmaydi."""
    lines = []
    lines.append(f"🔑 Botda INTERNAL_API_KEY: {'o\'rnatilgan (' + str(len(INTERNAL_API_KEY)) + ' belgi)' if INTERNAL_API_KEY else '❌ O\'RNATILMAGAN'}")
    t0 = asyncio.get_event_loop().time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/health", timeout=aiohttp.ClientTimeout(total=60)) as resp:
                ms = int((asyncio.get_event_loop().time() - t0) * 1000)
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                if resp.status != 200:
                    lines.append(f"🖥 Server: ❌ HTTP {resp.status} — server ishlamayapti yoki yangi kod noto'g'ri yuklangan (Render Logs'ni ko'ring)")
                    return lines
                lines.append(f"🖥 Server: ✅ javob berdi ({ms} ms{', uyg\'ongan' if ms > 8000 else ''})")
                lines.append(f"🗄 Baza (Firebase): {'✅ ulangan' if data.get('firebase') else '❌ ULANMAGAN — Render Environment\'dagi FIREBASE sozlamalarini tekshiring'}")
            headers = {"X-Internal-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {}
            async with session.post(f"{BACKEND_URL}/api/admin/target-id", headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                if data.get("success"):
                    lines.append("🔐 Kalit: ✅ server bilan mos (admin ham topildi)")
                elif resp.status == 401:
                    lines.append("🔐 Kalit: ❌ MOS EMAS — bot va server INTERNAL_API_KEY qiymatlari har xil (yoki bot xizmatida yo'q)")
                elif "Admin topilmadi" in str(data.get("error")):
                    lines.append("🔐 Kalit: ✅ mos. ⚠️ Lekin bazada isAdmin: true bo'lgan foydalanuvchi yo'q")
                else:
                    lines.append(f"🔐 Kalit: ⚠️ tekshirib bo'lmadi ({data.get('error') or 'HTTP ' + str(resp.status)})")
    except asyncio.TimeoutError:
        lines.append("🖥 Server: ❌ 60 soniyada javob bermadi")
    except Exception as e:
        lines.append(f"🖥 Server: ❌ ulanib bo'lmadi ({type(e).__name__})")
    return lines

@dp.message(Command("holat"))
async def holat_command(message: types.Message):
    await message.answer("🔎 Tekshiryapman (1 daqiqagacha cho'zilishi mumkin)...")
    lines = await backend_status()
    await message.answer("📋 Aloqa holati\n\n" + "\n".join(lines))

@dp.message(Command("id"))
async def id_command(message: types.Message):
    uid = message.from_user.id
    st = await check_admin(uid)
    status = "✅ administrator" if st else ("❌ administrator emas" if st is False else "⏳ server javob bermadi, 1 daqiqadan so'ng qayta yozing")
    text = f"🆔 Sizning Telegram ID: {uid}\nHolat: {status}"
    if st is False:
        text += f"\n\nAgar siz administrator bo'lsangiz: Firebase, Realtime Database, users, {uid} ichida isAdmin: true bo'lishi kerak (aynan shu raqam kalit bo'lsin)."
    await message.answer(text)

@dp.message(Command("xabar", "savol"))
async def xabar_command(message: types.Message, state: FSMContext):
    if not await admin_gate(message):
        return
    await state.set_state(Broadcast.waiting_text)
    await message.answer(
        "📣 Hammaga yubormoqchi bo'lgan xabarni yuboring: matn, rasm, video, fayl yoki post "
        "(kanaldan forward qilsangiz ham bo'ladi).\n\nBekor qilish: /bekor"
    )

@dp.message(Command("bekor"), StateFilter(Broadcast.waiting_text, Broadcast.confirm))
async def xabar_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.")

# Buyruqlar (/ bilan boshlanadigan matn) xabar sifatida qabul qilinmaydi — ular o'z handleriga o'tadi
@dp.message(Broadcast.waiting_text, lambda m: not (m.text or "").startswith("/"))
async def xabar_receive(message: types.Message, state: FSMContext):
    # Xavfsizlik uchun qayta tekshiramiz — kimdir shu oralig'da holatni qo'lga kirita olmasin
    if not await is_admin_user(message.from_user.id):
        await state.clear()
        await message.answer("Bu buyruq faqat administrator uchun.")
        return
    if message.media_group_id:
        await message.answer("Albom (bir nechta rasm) qo'llab-quvvatlanmaydi. Bitta rasm yoki bitta post yuboring.")
        return
    try:
        await bot.copy_message(chat_id=message.chat.id, from_chat_id=message.chat.id, message_id=message.message_id)
    except Exception as e:
        print("[bot] xabar ko'rinishi xatosi:", e)
        await message.answer("❌ Bu turdagi xabarni yuborib bo'lmaydi. Matn, rasm, video yoki fayl yuboring.")
        return
    await state.update_data(src_chat=message.chat.id, src_msg=message.message_id)
    await state.set_state(Broadcast.confirm)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Hammaga yuborish", callback_data="bc:go"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bc:no"),
    ]])
    await message.answer("👆 Xabar hamma foydalanuvchiga shunday ko'rinadi. Botning barcha foydalanuvchilariga yuboraymi?", reply_markup=kb)

@dp.callback_query(Broadcast.confirm, F.data.in_({"bc:go", "bc:no"}))
async def xabar_confirm(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await state.clear()
    if callback.data == "bc:no":
        await callback.message.edit_text("❌ Bekor qilindi.")
        return
    if not await is_admin_user(callback.from_user.id):
        await callback.message.edit_text("Bu amal faqat administrator uchun.")
        return
    src_chat, src_msg = data.get("src_chat"), data.get("src_msg")
    if not src_chat or not src_msg:
        await callback.message.edit_text("Xabar topilmadi. /xabar dan qaytadan boshlang.")
        return
    await callback.message.edit_text("⏳ Yuborish boshlanmoqda...")
    result = await send_broadcast_copy(callback.from_user.id, src_chat, src_msg)
    if result and result.get("success"):
        await callback.message.edit_text(f"✅ Yuborish boshlandi: {result.get('total', 0)} ta foydalanuvchiga. Tugagach hisobot keladi.")
    else:
        err = (result or {}).get("error") or "serverga ulanib bo'lmadi"
        await callback.message.edit_text(f"❌ Yuborilmadi: {err}")

# ================== ESLATMA: /eslatma — hammaga; avtomatik har kuni 18:00 ==================
async def nudge_api(path: str, payload: dict) -> Union[dict, None]:
    headers = {"X-Internal-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BACKEND_URL}{path}", headers=headers, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=25)) as resp:
                try:
                    return await resp.json()
                except Exception:
                    # JSON emas — odatda serverda yangi kod yo'q (404) yoki server hali uyg'onmagan (502/503)
                    hint = {404: "serverda yangi kod yo'q (eslatma.js/viktorina.js/server.js yuklanmagan?)",
                            502: "server uyg'onmoqda, 1 daqiqadan so'ng qayta urining",
                            503: "server uyg'onmoqda, 1 daqiqadan so'ng qayta urining"}.get(resp.status, "kutilmagan javob")
                    return {"success": False, "error": f"Server javobi {resp.status}: {hint}"}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Server javob bermadi (vaqt tugadi). Render uxlab qolgan bo'lishi mumkin — 1 daqiqadan so'ng qayta urining"}
    except Exception as e:
        print("[bot]", path, "xatosi:", e)
        return None

@dp.message(Command("eslatma"))
async def eslatma_admin(message: types.Message):
    """/eslatma — hammaga eslatma (standart matn) · /eslatma <matn> — shu matn hammaga · test / on / off"""
    if not await admin_gate(message):
        return
    arg = (message.text or "").partition(" ")[2].strip()
    low = arg.lower()
    if low in ("hozir", "hamma", "status", "vaqt", "run", "time", "all"):
        await message.answer("Endi oddiy: faqat /eslatma deb yozing, shuning o'zi hammaga yuboradi.")
        return
    if low in ("on", "off"):
        r = await nudge_api("/api/admin/nudge", {"adminUserId": str(message.from_user.id), "action": low})
        if not r or not r.get("success"):
            await message.answer(f"❌ {(r or {}).get('error') or 'serverga ulanib bo' + chr(39) + 'lmadi'}")
        else:
            await message.answer("✅ Avtomatik eslatma yoqildi (har kuni 18:00)." if low == "on" else "⏸ Avtomatik eslatma to'xtatildi. /eslatma bilan qo'lda yuborish ishlayveradi.")
        return
    if low == "test":
        r = await nudge_api("/api/admin/nudge", {"adminUserId": str(message.from_user.id), "action": "test"})
        if r and r.get("success"):
            await message.answer("📨 Sinov xabari faqat sizga yuborildi.")
        else:
            await message.answer(f"❌ {(r or {}).get('error') or 'serverga ulanib bo' + chr(39) + 'lmadi'}")
        return
    r = await nudge_api("/api/admin/nudge", {"adminUserId": str(message.from_user.id), "action": "send", "text": arg})
    if r and r.get("success"):
        await message.answer(f"🚀 Eslatma {r.get('total', 0)} ta foydalanuvchiga yuborilmoqda. Tugagach hisobot keladi.")
    else:
        await message.answer(f"❌ {(r or {}).get('error') or 'serverga ulanib bo' + chr(39) + 'lmadi'}")

@dp.message(Command("eslatmatest"))
async def eslatmatest_command(message: types.Message):
    """Sinov: eslatma faqat sizga yuboriladi (hammaga emas)."""
    if not await admin_gate(message):
        return
    r = await nudge_api("/api/admin/nudge", {"adminUserId": str(message.from_user.id), "action": "test"})
    if r and r.get("success"):
        await message.answer("📨 Sinov xabari faqat sizga yuborildi.")
    else:
        await message.answer(f"❌ {(r or {}).get('error') or 'serverga ulanib bo' + chr(39) + 'lmadi'}")

# ================== KUNLIK VIKTORINA (8 savol) va HAFTALIK HISOBOT ==================
@dp.message(Command("kunlik"))
async def kunlik_admin(message: types.Message):
    """/kunlik — hozir yuborish · /kunlik test — faqat sizga · /kunlik on|off — avtomatik (har kuni 10:00)"""
    if not await admin_gate(message):
        return
    arg = (message.text or "").partition(" ")[2].strip().lower()
    action = {"": "send", "test": "test", "on": "on", "off": "off"}.get(arg)
    if not action:
        await message.answer("/kunlik — hozir hammaga · /kunlik test — faqat sizga · /kunlik on | off")
        return
    r = await nudge_api("/api/admin/daily", {"adminUserId": str(message.from_user.id), "action": action})
    if not r or not r.get("success"):
        await message.answer(f"❌ {(r or {}).get('error') or 'serverga ulanib bo' + chr(39) + 'lmadi'}")
    elif action in ("on", "off"):
        await message.answer("✅ Kunlik viktorina yoqildi (har kuni 10:00)." if action == "on" else "⏸ Kunlik viktorina to'xtatildi.")
    else:
        await message.answer("🚀 Kunlik viktorina yuborilmoqda (8 savol + natija so'rovnomasi). Tugagach hisobot keladi.")

@dp.message(Command("hisobot"))
async def hisobot_admin(message: types.Message):
    """/hisobot — haftalik hisobotni hozir hammaga · /hisobot test — faqat sizga (har yakshanba 20:00 avtomatik)"""
    if not await admin_gate(message):
        return
    arg = (message.text or "").partition(" ")[2].strip().lower()
    r = await nudge_api("/api/admin/daily", {"adminUserId": str(message.from_user.id), "action": "weeklytest" if arg == "test" else "weekly"})
    if not r or not r.get("success"):
        await message.answer(f"❌ {(r or {}).get('error') or 'serverga ulanib bo' + chr(39) + 'lmadi'}")
    else:
        await message.answer("📨 Sinov hisoboti sizga yuborilmoqda." if arg == "test" else "🚀 Haftalik hisobot yuborilmoqda.")

@dp.message(Command("eslatmalar"))
async def eslatmalar_old(message: types.Message):
    await message.answer("Endi oddiy: faqat /eslatma deb yozing — hammaga yuboriladi. Avtomatik ravishda har kuni 18:00 da ham o'zi ketadi.")

# ================== ADMIN: VIKTORINA (quiz so'rovnomasi, tahlil bilan) ==================
# /viktorina — savol, variantlar, to'g'ri javob va tahlilni BITTA xabarda yuborasiz; bot avval ko'rsatadi,
# tasdiqlansa hammaga Telegram quiz ko'rinishida yuboriladi. /natija — kim nechta yechganini ko'rsatadi.
QUIZ_HELP = (
    "🧠 Viktorinani bitta xabarda shu shaklda yuboring:\n\n"
    "Suvning kimyoviy formulasi qaysi?\n"
    "A) CO₂\nB) H₂O\nC) NaCl\nD) O₂\n"
    "Javob: B\n"
    "Tahlil: Suv ikkita vodorod va bitta kislorod atomidan iborat.\n\n"
    "• Variantlar 2–10 ta (A, B, C...). To'g'ri javob «Javob: B» qatori yoki variant oldiga * belgisi bilan.\n"
    "• «Tahlil:» ixtiyoriy — odam javob bergach shu matn chiqadi (200 belgigacha).\n"
    "• Savol 300, har bir variant 100 belgigacha.\n\nBekor qilish: /bekor"
)
Q_OPT_RE = re.compile(r"^\s*([*+✓✔]\s*)?\(?([A-Ja-j])[\.\)\:]\s*(.*?)\s*([✓✔]|\(to'g'ri\))?\s*$")
Q_ANS_RE = re.compile(r"^\s*(?:to['ʻ’]?g['ʻ’]?ri\s+javob|javob|kalit|answer)\s*[:\-–=]?\s*\(?([A-Ja-j])\)?\.?\s*$", re.I)
Q_EXP_RE = re.compile(r"^\s*(?:tahlil|izoh|tushuntirish|sharh|explanation)\s*[:\-–]\s*(.*)$", re.I)

def parse_quiz(text: str):
    """(dict, None) yoki (None, xato matni)."""
    q_lines, opts, correct, exp = [], [], None, None
    for raw in (text or "").replace("\r", "").split("\n"):
        s = raw.strip()
        if exp is not None:
            exp.append(s)
            continue
        if not s:
            continue
        m = Q_EXP_RE.match(s)
        if m:
            exp = [m.group(1)]
            continue
        m = Q_ANS_RE.match(s)
        if m:
            correct = ord(m.group(1).upper()) - 65
            continue
        m = Q_OPT_RE.match(s)
        if m and q_lines:
            idx = ord(m.group(2).upper()) - 65
            if idx != len(opts):
                return None, "Variantlar A, B, C... tartibida bo'lsin."
            opts.append(m.group(3).strip())
            if m.group(1) or m.group(4):
                correct = idx
            continue
        if opts:
            return None, f"Tushunarsiz qator: «{s[:40]}». Variantlardan keyin faqat «Javob:» va «Tahlil:» bo'lishi mumkin."
        q_lines.append(s)
    question = re.sub(r"^\s*(?:№\s*)?\d+\s*[\.\)\-:]\s*", "", " ".join(q_lines)).strip()
    explanation = " ".join(x for x in (exp or []) if x).strip()
    if not question:
        return None, "Savol matni topilmadi."
    if len(question) > 300:
        return None, f"Savol {len(question)} belgi — 300 dan oshmasin."
    if len(opts) < 2 or len(opts) > 10:
        return None, "Variantlar 2 tadan 10 tagacha bo'lsin (A) B) C)...)."
    for i, o in enumerate(opts):
        if not o or len(o) > 100:
            return None, f"{chr(65 + i)} variant bo'sh yoki 100 belgidan uzun."
    if correct is None or correct >= len(opts):
        return None, "To'g'ri javob ko'rsatilmagan. «Javob: B» qatorini yozing."
    if len(explanation) > 200:
        return None, f"Tahlil {len(explanation)} belgi — Telegram 200 dan oshiqqa ruxsat bermaydi. Qisqartiring."
    return {"question": question, "options": opts, "correct": correct, "explanation": explanation}, None

@dp.message(Command("viktorina", "quiz"))
async def viktorina_command(message: types.Message, state: FSMContext):
    if not await admin_gate(message):
        return
    await state.set_state(Quiz.waiting)
    await message.answer(QUIZ_HELP)

@dp.message(Command("bekor"), StateFilter(Quiz.waiting, Quiz.confirm))
async def viktorina_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.")

@dp.message(Quiz.waiting, lambda m: not (m.text or "").startswith("/"))
async def viktorina_receive(message: types.Message, state: FSMContext):
    if not await is_admin_user(message.from_user.id):
        await state.clear()
        await message.answer("Bu buyruq faqat administrator uchun.")
        return
    quiz, err = parse_quiz(message.text or "")
    if err:
        await message.answer(f"❌ {err}\n\nTuzatib qayta yuboring yoki /bekor.")
        return
    try:
        await bot.send_poll(chat_id=message.chat.id, question=quiz["question"], options=quiz["options"], type="quiz",
                            correct_option_id=quiz["correct"], explanation=quiz["explanation"] or None, is_anonymous=False)
    except Exception as e:
        print("[bot] viktorina ko'rinishi xatosi:", e)
        await message.answer("❌ Telegram bu viktorinani qabul qilmadi. Matnni tekshirib qayta yuboring.")
        return
    await state.update_data(quiz=quiz)
    await state.set_state(Quiz.confirm)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Hammaga yuborish", callback_data="qz:go"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="qz:no"),
    ]])
    await message.answer("👆 Viktorina hamma foydalanuvchiga shunday ko'rinadi (javob bersangiz, tahlil chiqadi). Yuboraymi?", reply_markup=kb)

@dp.callback_query(Quiz.confirm, F.data.in_({"qz:go", "qz:no"}))
async def viktorina_confirm(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await state.clear()
    if callback.data == "qz:no":
        await callback.message.edit_text("❌ Bekor qilindi.")
        return
    if not await is_admin_user(callback.from_user.id):
        await callback.message.edit_text("Bu amal faqat administrator uchun.")
        return
    quiz = data.get("quiz")
    if not quiz:
        await callback.message.edit_text("Viktorina topilmadi. /viktorina dan qaytadan boshlang.")
        return
    await callback.message.edit_text("⏳ Yuborish boshlanmoqda...")
    r = await nudge_api("/api/admin/quiz/send", {"adminUserId": str(callback.from_user.id), **quiz})
    if r and r.get("success"):
        await callback.message.edit_text(f"✅ Viktorina {r.get('total', 0)} ta foydalanuvchiga yuborilmoqda. Tugagach hisobot keladi.\n\nNatijani istalgan payt ko'rish: /natija")
    else:
        await callback.message.edit_text(f"❌ Yuborilmadi: {(r or {}).get('error') or 'serverga ulanib bo' + chr(39) + 'lmadi'}")

# Foydalanuvchi viktorinaga javob berdi -> serverga yozamiz (faqat shu botdan yuborilgan so'rovnomalar uchun keladi)
@dp.poll_answer()
async def on_poll_answer(poll_answer: types.PollAnswer):
    await nudge_api("/api/quiz/answer", {"pollId": poll_answer.poll_id, "userId": str(poll_answer.user.id), "optionIds": list(poll_answer.option_ids)})

def format_quiz_stats(r: dict) -> str:
    q, answered, correct = r["quiz"], r["answered"], r["correct"]
    sent = q.get("sent", 0)
    pa = f" ({round(answered * 100 / sent)}%)" if sent else ""
    pc = f" ({round(correct * 100 / answered)}%)" if answered else ""
    lines = [
        "📊 Viktorina natijasi" + ("  ⏳ yuborilmoqda..." if q.get("status") == "sending" else ""),
        f"❓ {q['question'][:150]}",
        "",
        f"📬 Yetkazildi: {sent} / {q.get('total', 0)}" + (f"  (bloklagan: {q['blocked']})" if q.get("blocked") else ""),
        f"✍️ Javob berdi: {answered}{pa}",
        f"✅ To'g'ri topdi: {correct}{pc}",
        f"❌ Noto'g'ri: {answered - correct}",
        "",
    ]
    for i, o in enumerate(q["options"]):
        n = r["perOption"][i]
        p = f" ({round(n * 100 / answered)}%)" if answered else ""
        lines.append(f"{chr(65 + i)}) {o[:40]} — {n}{p}" + ("  ✅" if i == q["correct"] else ""))
    return "\n".join(lines)

def stats_keyboard(quiz_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"qs:{quiz_id}")]])

@dp.message(Command("natija"))
async def natija_command(message: types.Message):
    if not await admin_gate(message):
        return
    parts = (message.text or "").split()
    back = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    r = await nudge_api("/api/admin/quiz/stats", {"adminUserId": str(message.from_user.id), "back": back})
    if not r or not r.get("success"):
        await message.answer(f"❌ {(r or {}).get('error') or 'serverga ulanib bo' + chr(39) + 'lmadi'}")
        return
    extra = f"\n\nOldingilari: /natija 2, /natija 3 ... (jami {r.get('count')} ta)" if r.get("count", 0) > 1 else ""
    await message.answer(format_quiz_stats(r) + extra, reply_markup=stats_keyboard(r["quiz"]["id"]))

@dp.callback_query(F.data.startswith("qs:"))
async def natija_refresh(callback: types.CallbackQuery):
    if not await is_admin_user(callback.from_user.id):
        await callback.answer("Faqat administrator uchun", show_alert=True)
        return
    r = await nudge_api("/api/admin/quiz/stats", {"adminUserId": str(callback.from_user.id), "quizId": callback.data[3:]})
    if not r or not r.get("success"):
        await callback.answer("Yangilab bo'lmadi", show_alert=True)
        return
    await callback.answer("Yangilandi")
    try:
        await callback.message.edit_text(format_quiz_stats(r), reply_markup=stats_keyboard(r["quiz"]["id"]))
    except Exception:
        pass  # matn o'zgarmagan bo'lsa, Telegram xato qaytaradi — bu normal

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
