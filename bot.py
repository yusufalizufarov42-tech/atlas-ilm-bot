import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. BotFather bergan token
BOT_TOKEN = "8816941209:AAEY4HG8ruVjoVF_50Ugbswb5vF5Ss-mwr4"

# 2. Kanalingiz username'i
CHANNEL_ID = "@atlas_ilm"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

def get_sub_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_ID[1:]}")],
            [InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="check_subscription")]
        ]
    )
    return keyboard

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    if await is_subscribed(message.from_user.id):
        await message.answer("Xush kelibsiz! Botdan foydalanishingiz mumkin.")
    else:
        await message.answer(
            "Botdan foydalanish uchun avval kanalimizga a'zo bo'ling:",
            reply_markup=get_sub_keyboard()
        )

@dp.callback_query(F.data == "check_subscription")
async def check_callback(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer("Rahmat! A'zolik tasdiqlandi. Endi botdan foydalanishingiz mumkin.")
    else:
        await callback.answer("Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)

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