import os
import time
import json
import asyncio
from sqlmodel import SQLModel, create_engine, Session, select, text, update
from utils import jalali
from collections import defaultdict
from utils.assets import (
    CHINESE_SIGNS,
    CHINESE_ELEMENTS,
    PERSIAN_MONTHS,
    CHINESE_SIGNS_FARSI,
    CHINESE_ELEMENTS_FARSI,
    dashboard_keyboard,
    is_user_member,
    is_valid_date,
    user_channel_check,
    insert_to_user_table,
    insert_to_kua_table,
    insert_to_zodiac_table,
    insert_to_mashhad_table,
    insert_to_fengshui_test_table,
    insert_to_fengshui_score_table,
    extract_chinese_year,
    calculate_kua_number,
    calculate_zodiac_animal,
    send_join_channel_button,
    forward_message_to_users,
    decade_buttons,
    year_buttons,
    month_buttons,
    day_buttons,
    gender_buttons,
    check_visit_count,
    check_register
)
from models import User, Kua, Zodiac, Mashhad, UserReplyState
from dotenv import load_dotenv
from telebot import apihelper
from telebot.async_telebot import AsyncTeleBot
from telebot.types import (
    BotCommand,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    CallbackQuery,
)



# ------------------------------------------------------------------------------
# Initials
# ------------------------------------------------------------------------------

# Load Environment Variables
load_dotenv()

# Temporary Storage For User Input Data
user_data = {}
user_mashhad_data = {}
user_kua_data = {}
user_zodiac_data = {}

# Your Channel Username
# CHANNELS = ["helekhobmalkhob", "aliravanbakhsh1"]
CHANNELS = ["helekhobmalkhob"]
# CHANNELS = ["HydroCodeChannel"]

# Maximum Visit
MAX_VISIT = 0
MAX_CALCULATION = 4

TEXT_KUA_MAX_VISIT = "تعداد محاسبات عدد شانس شما به پایان رسیده است. برای محاسبه عدد شانس با یک شماره جدید وارد بات شوید!"
TEXT_ZODIAC_MAX_VISIT = "تعداد محاسبات زودیاک تولد شما به پایان رسیده است. برای محاسبه زودیاک تولد با یک شماره جدید وارد بات شوید!"



with open('utils/zodiac.json', 'r', encoding='utf-8') as file:
    zodiac_data = json.load(file)

with open('utils/kua.json', 'r', encoding='utf-8') as file:
    kua_data = json.load(file)

with open('utils/zodiac_animal_dataset.json', 'r', encoding='utf-8') as file:
    zodiac_animal_dataset = json.load(file)

with open('utils/kua_elements.json', 'r', encoding='utf-8') as file:
    kua_element = json.load(file)



# ------------------------------------------------------------------------------
# Create Bot
# ------------------------------------------------------------------------------

# Create Bot
bot = AsyncTeleBot(
    token=os.getenv("Bot_API_Token")
)



# ------------------------------------------------------------------------------
# Database
# ------------------------------------------------------------------------------
DATABASE_NAME = 'database.db'
engine = create_engine(f"sqlite:///{DATABASE_NAME}", pool_size=500, max_overflow=500)
SQLModel.metadata.create_all(engine)



# ------------------------------------------------------------------------------ #
#                           Handle /start Command
# ------------------------------------------------------------------------------ #

@bot.message_handler(commands=['start'])
async def start_command(message):
    user_id = message.chat.id
    with Session(engine) as session:
        statement = select(User).where(User.user_id == user_id)
        existing_user = session.exec(statement).first()
    if existing_user:
        markup = dashboard_keyboard()
        await bot.send_message(
            chat_id=message.chat.id,
            text=(
                f"سلام، خوشحالم که دوباره تو رو میبینم {existing_user.given_name}!\n\n"
                "اینجا چندتا گزینه وجود داره که میتونی انتخاب کنی:"
            ),
            reply_markup=markup
        )
    else:
        user_data[message.chat.id] = "awaiting_phone"
        phone_button = KeyboardButton(
            text="👈🏻ارسال شماره 👉🏻", 
            request_contact=True
        )
        keyboard = ReplyKeyboardMarkup(
            resize_keyboard=True,
            one_time_keyboard=True
        )
        keyboard.add(phone_button)
        await bot.send_message(
            chat_id=message.chat.id,
            text=(
            "💡 روی دکمه «ارسال شماره» بزن تا وارد بات بشی:"
        ),
            parse_mode="Markdown",
            reply_markup=keyboard
        )


@bot.message_handler(content_types=['contact'])
async def handle_contact(message):
    phone_number = message.contact.phone_number
    user_data[message.chat.id] = {
        "state": "awaiting_name",
        "phone_number": phone_number
    }
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"سپاس از شما. لطفا اسم و فامیل خودت را به فارسی این زیر بنویس:",
        reply_markup=ReplyKeyboardRemove()
    )


@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get("state") == "awaiting_name")
async def handle_name(message):
    name = message.text
    phone_number = user_data[message.chat.id]["phone_number"]    
    user_data[message.chat.id] = {
        "state": "awaiting_city",
        "phone_number": phone_number,
        "name": name,
    }
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"بسیار عالی! آخرین سوال. {name} میشه بگی از کدوم شهر هستی؟",
    )


@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get("state") == "awaiting_city")
async def handle_city(message):
    user_id = message.chat.id
    first_name = message.chat.first_name
    try:
        last_name = message.chat.get('last_name', None)
    except:
        last_name = None
    try:
        username = message.chat.get('username', None)
    except:
        username = None
    phone_number = user_data[message.chat.id]["phone_number"]
    given_name = user_data[message.chat.id]["name"]
    city = message.text
    print("Start: ", user_id)
    print("First Name: ", first_name)
    print("Last Name: ", last_name)
    print("Username: ", username)
    print("Phone Number: ", phone_number)
    print("Given Name: ", given_name)
    print("City: ", city)
    print("End: ", user_id)
    insert_to_user_table(
        engine=engine,
        user_id=user_id,
        username=username,
        phone_number=phone_number,
        first_name=first_name,
        last_name=last_name,
        given_name=given_name,
        city=city
    )
    del user_data[message.chat.id]
    markup = dashboard_keyboard()
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"خیلی ممنون، {given_name} عزیز از {city}! اطلاعاتت ذخیره شد. حالا می‌تونی از این گزینه‌ها استفاده کنی:",
        reply_markup=markup
    )

# ------------------------------------------------------------------------------ #
#                              Handle Dashboard Command
# ------------------------------------------------------------------------------ #

@bot.callback_query_handler(func=lambda call: call.data in ["mashhad_button", "kua_button", "zodiac_button", "help_button", "start_button", "fengshui_test_button"])
async def handle_dashboard_callbacks(call):
    user_id=call.message.chat.id
    if call.data == "mashhad_button":
        if await user_channel_check(
            engine=engine,
            table=Mashhad,
            bot=bot,
            message=call.message,
            user_id=user_id,
            max_visit=MAX_VISIT,
            channels=CHANNELS
        ):
            await mashhad_command(call.message)
    elif call.data == "kua_button":
        if await user_channel_check(
            engine=engine,
            table=Kua,
            bot=bot,
            message=call.message,
            user_id=user_id,
            max_visit=MAX_VISIT,
            channels=CHANNELS
        ):
            await kua_command(call.message)
    elif call.data == "zodiac_button":
        if await user_channel_check(
            engine=engine,
            table=Zodiac,
            bot=bot,
            message=call.message,
            user_id=user_id,
            max_visit=MAX_VISIT,
            channels=CHANNELS
        ):
            await zodiac_command(call.message)
    elif call.data == "help_button":
        await start_command(call.message)
    elif call.data == "fengshui_test_button":
        await start_fengshui_test(call.message)
    elif call.data == "start_button":
        await start_command(call.message)



@bot.callback_query_handler(func=lambda call: call.data == "confirm_join")
async def handle_confirm_join(call):
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=None
    )


    if await user_channel_check(
            engine=engine,
            table=Kua,
            bot=bot,
            message=call.message,
            user_id=call.message.chat.id,
            max_visit=MAX_VISIT,
            channels=CHANNELS
        ):
            markup = dashboard_keyboard()
            await bot.send_message(
                chat_id=call.message.chat.id,
                text="عضویت شما تایید شد ✅. حالا می‌توانید از امکانات ربات استفاده کنید.",
                reply_markup=markup
            )


# ------------------------------------------------------------------------------ #
#                              Handle /mashhad Command
# ------------------------------------------------------------------------------ #
# @bot.message_handler(commands=['mashhad'])
# async def mashhad_command(message):
#     user_id = message.chat.id 
#     if await user_channel_check(
#         engine=engine,
#         table=Mashhad,
#         bot=bot,
#         message=message,
#         user_id=user_id,
#         max_visit=MAX_VISIT,
#         channels=CHANNELS
#     ):
#         if check_register(
#             engine=engine,
#             table=Mashhad,
#             user_id=user_id,
#         ):
#             await bot.send_message(
#                 chat_id=message.chat.id,
#                 text=(
#                     "قراره یک نفر برنده سفر مشهد و زیارت حرم امام رضا (ع) بشه.\n\n"
#                     "اطلاعاتی که در ادامه ازت خواسته میشه رو با دقت وارد کن تا ثبت نام اولیه‌ات تکمیل بشه.\n\n"
#                 ),
#                 parse_mode="HTML",
#             )
#             user_mashhad_data[message.chat.id] = {
#                 "state": "awaiting_name_mashhad",
#             }
#             await bot.send_message(
#                 chat_id=message.chat.id,
#                 text=f"لطفا اسم و فامیل خودت را به فارسی این زیر بنویس:",
#                 reply_markup=ReplyKeyboardRemove()
#             )
#         else:
#             await bot.send_message(
#                 chat_id=message.chat.id,
#                 text="شما قبلا ثبت نام اولیه را انجام داده‌اید، نیاز به ثبت نام مجدد نمی‌باشد!"
#             )


# @bot.message_handler(func=lambda message: user_mashhad_data.get(message.chat.id, {}).get("state") == "awaiting_name_mashhad")
# async def handle_mashhad_name(message):
#     name = message.text
#     user_mashhad_data[message.chat.id] = {
#         "state": "awaiting_mashhad_city",
#         "name": name,
#     }
#     await bot.send_message(
#         chat_id=message.chat.id,
#         text=f"لطفا شهر خودت را به فارسی این زیر بنویس:",
#     )


# @bot.message_handler(func=lambda message: user_mashhad_data.get(message.chat.id, {}).get("state") == "awaiting_mashhad_city")
# async def handle_mashhad_city(message):
#     user_id = message.chat.id
#     name = user_mashhad_data[message.chat.id]["name"]
#     city = message.text
#     print("Start: ", user_id)
#     print("Name: ", name)
#     print("City: ", city)
#     print("End: ", user_id)
#     insert_to_mashhad_table(
#         engine=engine,
#         user_id=user_id,
#         name=name,
#         city=city
#     )
#     del user_mashhad_data[message.chat.id]
#     markup = dashboard_keyboard()
#     await bot.send_message(
#         chat_id=message.chat.id,
#         text=(
#             "شرایط این جایزه رو کامل بخون\n"
#             "قراره یک نفر مهمون خودم بیاد مشهد تا بریم زیارت امام رضا 🌷\n\n"
#             "چله ژورنال ثروت :\n"
#             "( کوچ 40 روزه )\n\n"
#             "💥40 کُد روزانه\n"
#             "💥40 روز شکرگزاری\n"
#             "💥40 روز باور فراوانی انرژی\n"
#             "ذهنی ، روحی ، جسمی ، محیط\n"
#             "( برگزاری در کانال خصوصی تلگرام و روبیکا )\n\n"
#             "🎁 هدیه ویژه : مدیتیشن پول \n"
#             "100 نفر اول\n\n"
#             "🎁🧳یک نفر برنده سفر مشهد و زیارت حرم امام رضا 💚🙏\n\n"
#             "🔺🔺🔺🔺کافیه توی این دوره شرکت کنی تا توی قرعه کشی سفر مشهد شانست رو امتحان کنی !\n\n"
#             "⏰️ثبت نام : از 15 بهمن \n"
#             "❗️فقط برای 300 نفر \n"
#             "✔️قیمت دوره : 1/280 تومان \n\n"
#             "🛑ظرفیت خیلی محدوده\n"
#             "اگه میخوای پیش ثبت نام کنی \n"
#             "به این آیدی پیام بده 👇🏼\n\n"
#             "@fereshtehelp"
#         ),
#         parse_mode="HTML",
#         reply_markup=markup
#     )


# ------------------------------------------------------------------------------ #
#                              Handle /kua Command
# ------------------------------------------------------------------------------ #
@bot.message_handler(commands=['kua'])
async def kua_command(message):    
    user_id = message.chat.id 
    if await user_channel_check(
        engine=engine,
        table=Kua,
        bot=bot,
        message=message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Kua,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            await bot.send_message(
                chat_id=message.chat.id,
                text=(
                    "اولین محاسبه‌گر دقیق عدد کوا با در نظر گرفتن تمامی استثنائات\n\n"
                    "💚برای اولین بار در ایران 💚\n\n"
                    "عدد کوا یا عدد شانس، علاوه بر نشان دادن عنصر وجودی ما‌، در چیدمان محیط به ما کمک می‌کند. کوانامبر نمایانگر جهات خوب و بد نشستن، ایستادن، کار کردن و خوابیدن است که به نوبه خود، روشی مجزا در فنگ‌شویی، تحت عنوان روش فنگ شویی فردی یا فنگشویی براساس عدد کوا است.\n\n"
                    "برای محاسبه عدد کوا کافیست تارخ تولد و جنسیت خود را در ادامه وارد کنید.\n\n"
                ),
                parse_mode="HTML",
            )
            await decade_buttons(
                bot=bot,
                chat_id=message.chat.id,
                callback_prefix="kua_decade_"
            )
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text=TEXT_KUA_MAX_VISIT
            )
            
            
        

@bot.callback_query_handler(func=lambda call: call.data.startswith("kua_decade_"))
async def kua_command_handle_decade_selection(call):
    user_id = call.message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Kua,
        bot=bot,
        message=call.message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Kua,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            selected_decade = call.data.split("_")[2]
            start_year = int(selected_decade)
            end_year = start_year + 9
            await year_buttons(
                bot=bot,
                chat_id=user_id,
                start_year=start_year,
                end_year=end_year,
                callback_prefix="kua_year_"
            )
            await bot.answer_callback_query(callback_query_id=call.id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_KUA_MAX_VISIT
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith("kua_year_"))
async def kua_command_handle_year_selection(call):
    user_id = call.message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Kua,
        bot=bot,
        message=call.message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Kua,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            birth_year = int(call.data.split("_")[2])
            user_kua_data[user_id] = {"birth_year": birth_year }
            await month_buttons(
                bot=bot, 
                chat_id=user_id,
                callback_prefix="kua_month_"
                )
            await bot.answer_callback_query(callback_query_id=call.id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_KUA_MAX_VISIT
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith("kua_month_"))
async def kua_command_handle_month_selection(call):
    user_id = call.message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Kua,
        bot=bot,
        message=call.message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Kua,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            birth_month = int(call.data.split("_")[2])
            user_kua_data[user_id]["birth_month"] = birth_month
            await day_buttons(
                bot=bot,
                chat_id=user_id,
                callback_prefix="kua_day_"
            )
            await bot.answer_callback_query(callback_query_id=call.id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_KUA_MAX_VISIT
            )

@bot.callback_query_handler(func=lambda call: call.data.startswith("kua_day_"))
async def kua_command_handle_day_selection(call):
    user_id = call.message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Kua,
        bot=bot,
        message=call.message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Kua,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            birth_day = int(call.data.split("_")[2])
            user_kua_data[user_id]["birth_day"] = birth_day
            await gender_buttons(
                bot=bot,
                chat_id=user_id,
                callback_prefix="kua_gender_"
            )
            await bot.answer_callback_query(callback_query_id=call.id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_KUA_MAX_VISIT
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith("kua_gender_"))
async def kua_command_handle_gender_selection(call):
    user_id = call.message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Kua,
        bot=bot,
        message=call.message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Kua,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            gender = call.data.split("_")[2]
            user_kua_data[user_id]["gender"] = gender
            birth_year = user_kua_data[user_id]["birth_year"]
            birth_month = user_kua_data[user_id]["birth_month"]
            birth_day = user_kua_data[user_id]["birth_day"]

            if not is_valid_date(int(birth_year), int(birth_month), int(birth_day)):
                await bot.send_message(
                    chat_id=user_id, 
                    text="تاریخ وارد شده اشتباه است. لطفا تاریخ را به صورت صحیح وارد کن!",
                )
                await decade_buttons(
                        bot=bot,
                        chat_id=user_id,
                        callback_prefix="kua_decade_"
                    )
                return

            birth_year_g, birth_month_g, birth_day_g = jalali.Persian((int(birth_year), int(birth_month), int(birth_day))).gregorian_tuple()
            
            # chinese_year = extract_chinese_year(
            #     date_string=f"{birth_year_g:04d}-{birth_month_g:02d}-{birth_day_g:02d}"
            # )

            kua_number = calculate_kua_number(
                kua_data=kua_data,
                birth_year=birth_year_g,
                gender=gender
            )

            await bot.send_message(
                chat_id=user_id,
                text=f"📝 اطلاعات دریافت‌ شده:\n- تاریخ تولد: {birth_year}/{birth_month}/{birth_day}\n- جنسیت: {'مرد' if gender == 'male' else 'زن'}"
            )
            
            # # Send Kua Number Result
            # file_path = os.path.abspath(f"./data/img/kua_number_{kua_number}.png")
            # if not os.path.exists(file_path):
            #     print("File not found:", file_path)
            # else:
            #     print("File founded:", file_path)
            # with open(file_path, "rb") as photo:
            #     print("File opened successfully", file_path)
            #     await bot.send_photo(
            #         chat_id=user_id,
            #         photo=photo,
            #         caption=f"عدد کوا شما «{kua_number}» می‌باشد!",
            #     )  
                    
            # # Send Kua Number Result
            # file_path_voice = os.path.abspath(f"./data/ویس_تکنیک_عدد_شانس.m4a")
            # if not os.path.exists(file_path_voice):
            #     print("File not found:", file_path_voice)
            # else:
            #     print("File founded:", file_path_voice)
            # with open(file_path_voice, "rb") as voice:
            #     print("File opened successfully", file_path_voice)
            #     await bot.send_audio(
            #         chat_id=user_id,
            #         audio=voice,
            #         caption=f"ویس تکنیک عدد شانس",
            #         timeout=60
            #     )         
            # kn = str(kua_number)
            # await bot.send_message(
            #     chat_id=user_id,
            #     text=(
            #         "برای ثبت نام به آیدی زیر پیام بده:\n\n"
            #         "@fereshtehelp\n"      
            #         "👆👆👆👆\n"      
            #     ),
            #     parse_mode="HTML",
            # )
            
                        
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"عدد کوا (شانس) شما {kua_number} میباشد.\n\n"
                    f"عنصر شما {kua_element[str(kua_number)]["element"]} است."
                ),
                parse_mode="HTML",
            )
            
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "سلام 🌱\n",
                    "خوشحالم که در مسیر نور و آگاهی قرار داری …\n\n"
                    "همین الان وارد کانال زیر بشو  چون به رایگان بهت گفتم که با توجه به اطلاعاتی که بدست آوردی امسال چه انرژی هایی برات فعاله!!!\n\n"
                    "🔹 به‌علاوه، یک پاکسازی ویژه «نگهبان نور» که  برای رفع دعا و طلسم و جادو و چشم زخم  و انرژی حسادت در سال ۲۰۲۶ باید حتما انجامش بدی چون تو رو دربرابر همه این خطر ها محافظت میکنه.\n\n"
                    "اگه هنوز وارد کانال تلگرام نشدی و این آموزش‌ها رو نداری،👇\n"
                    "همین الان روی لینک زیر بزن و وارد شو\n"
                    "تا از این اطلاعات ارزشمند جا نمونی\n\n"
                    "https://t.me/fereshte2026\n\n"
                    "سوالی هم داشتی از آیدی زیر بپرس 👇🏼\n"
                    "@fereshtehelp"
                ),
                parse_mode="HTML",
            )

            with Session(engine) as session:
                statement = select(Kua).where(Kua.user_id == user_id)
                user = session.exec(statement).first()
                if user:
                    count_visit = user.count_visit + 1
                else:
                    count_visit = 1
                    
            
            insert_to_kua_table(
                engine=engine,
                user_id=user_id,
                gender=gender,
                birth_date=f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}",
                kua_number=kua_number,
                count_visit=count_visit
            )

            user_kua_data.pop(user_id, None)
            markup = dashboard_keyboard()
            await bot.send_message(
                chat_id=user_id,
                text=f"اینجا چندتا گزینه وجود داره که میتونی انتخاب کنی:",
                reply_markup=markup
            )
            await bot.answer_callback_query(callback_query_id=call.id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_KUA_MAX_VISIT
            )


# ------------------------------------------------------------------------------ #
#                              Handle /zodiac Command
# ------------------------------------------------------------------------------ #

@bot.message_handler(commands=['zodiac'])
async def zodiac_command(message):    
    user_id = message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Zodiac,
        bot=bot,
        message=message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Zodiac,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "زودیاک چینی، یا شنگ شیائو (生肖)، یک چرخه 12 ساله تکرار شونده از نشانه های حیوانات و ویژگی های نسبت داده شده به آنها، بر اساس تقویم قمری است. به ترتیب، حیوانات زودیاک عبارتند از: موش، گاو، ببر، خرگوش، اژدها، مار، اسب، بز، میمون، خروس، سگ، خوک. سال نو قمری یا جشنواره بهار، انتقال از یک حیوان به حیوان دیگر را نشان می‌دهد.\n\n"
                    "علامت زودیاک شما چیست؟ برای محاسبه علامت زودیاک کافیست تارخ تولد خود را در ادامه وارد کنید.\n\n"
                ),
                parse_mode="HTML",
            )
            await decade_buttons(
                bot=bot,
                chat_id=user_id,
                callback_prefix="zodiac_decade_"
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_ZODIAC_MAX_VISIT
            )
        

@bot.callback_query_handler(func=lambda call: call.data.startswith("zodiac_decade_"))
async def zodiac_command_handle_decade_selection(call):
    user_id = call.message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Zodiac,
        bot=bot,
        message=call.message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Zodiac,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            selected_decade = call.data.split("_")[2]
            start_year = int(selected_decade)
            end_year = start_year + 9
            await year_buttons(
                bot=bot,
                chat_id=user_id,
                start_year=start_year,
                end_year=end_year,
                callback_prefix="zodiac_year_"
            )
            await bot.answer_callback_query(callback_query_id=call.id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_ZODIAC_MAX_VISIT
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith("zodiac_year_"))
async def zodiac_command_handle_year_selection(call):
    user_id = call.message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Zodiac,
        bot=bot,
        message=call.message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Zodiac,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            birth_year = int(call.data.split("_")[2])
            user_zodiac_data[user_id] = {"birth_year": birth_year }
            await month_buttons(
                bot=bot, 
                chat_id=user_id,
                callback_prefix="zodiac_month_"
                )
            await bot.answer_callback_query(callback_query_id=call.id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_ZODIAC_MAX_VISIT
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith("zodiac_month_"))
async def zodiac_command_handle_month_selection(call):
    user_id = call.message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Zodiac,
        bot=bot,
        message=call.message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Zodiac,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            birth_month = int(call.data.split("_")[2])
            user_zodiac_data[user_id]["birth_month"] = birth_month
            await day_buttons(
                bot=bot,
                chat_id=user_id,
                callback_prefix="zodiac_day_"
            )
            await bot.answer_callback_query(callback_query_id=call.id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_ZODIAC_MAX_VISIT
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith("zodiac_day_"))
async def zodiac_command_handle_day_selection(call):
    user_id = call.message.chat.id
    if await user_channel_check(
        engine=engine,
        table=Zodiac,
        bot=bot,
        message=call.message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_visit_count(
            engine=engine,
            table=Zodiac,
            user_id=user_id,
            max_calculation=MAX_CALCULATION
        ):
            birth_day = int(call.data.split("_")[2])
            user_zodiac_data[user_id]["birth_day"] = birth_day

            birth_year = user_zodiac_data[user_id]["birth_year"]
            birth_month = user_zodiac_data[user_id]["birth_month"]
            birth_day = user_zodiac_data[user_id]["birth_day"]

            if not is_valid_date(int(birth_year), int(birth_month), int(birth_day)):
                await bot.send_message(
                    chat_id=user_id, 
                    text="تاریخ وارد شده اشتباه است. لطفا تاریخ را به صورت صحیح وارد کن!",
                )
                await decade_buttons(
                        bot=bot,
                        chat_id=user_id,
                        callback_prefix="zodiac_decade_"
                    )
                return

            await bot.send_message(
                chat_id=user_id,
                text=f"📝 اطلاعات دریافت‌ شده:\n- تاریخ تولد: {birth_year}/{birth_month}/{birth_day}"
            )
            
            birth_year_g, birth_month_g, birth_day_g = jalali.Persian((int(birth_year), int(birth_month), int(birth_day))).gregorian_tuple()
            
            chinese_year = extract_chinese_year(
                date_string=f"{birth_year_g:04d}-{birth_month_g:02d}-{birth_day_g:02d}"
            )
            
            chinese_sign_eng = calculate_zodiac_animal(
                zodiac_animal_dataset=zodiac_animal_dataset,
                birth_year=birth_year_g,
            )
            
            chinese_sign = CHINESE_SIGNS[int(chinese_year % 12)]
            
            
            chinese_element = CHINESE_ELEMENTS[int(chinese_year % 10) // 2]
            
            file_path = os.path.abspath(f"./data/img/zodiac_{chinese_sign_eng}.png")
            if not os.path.exists(file_path):
                print("File not found:", file_path)
            else:
                print("File founded:", file_path)
            with open(file_path, "rb") as photo:
                print("File opened successfully", file_path)
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=f"زودیاک تولد شما «{CHINESE_SIGNS_FARSI[chinese_sign_eng]}» می‌باشد!",
                )


            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"{zodiac_data[chinese_sign_eng]["description"]}\n\n"
                    # f"عددهای شانس شما: {zodiac_data[chinese_sign]["lucky_numbers"]}\n\n"
                    # f"رنگ‌های شانس شما: {zodiac_data[chinese_sign]["lucky_colors"]}\n\n"
                )
            )

            #         # Send Kua Number Result
            # file_path_voice = os.path.abspath(f"./data/ویس_تکنیک_عدد_شانس.m4a")
            # if not os.path.exists(file_path_voice):
            #     print("File not found:", file_path_voice)
            # else:
            #     print("File founded:", file_path_voice)
            # with open(file_path_voice, "rb") as voice:
            #     print("File opened successfully", file_path_voice)
            #     await bot.send_audio(
            #         chat_id=user_id,
            #         audio=voice,
            #         caption=f"ویس تکنیک عدد شانس",
            #         timeout=60
            #     )


            await bot.send_message(
                chat_id=user_id,
                text=(
                    "سلام 🌱\n",
                    "خوشحالم که در مسیر نور و آگاهی قرار داری …\n\n"
                    "همین الان وارد کانال زیر بشو  چون به رایگان بهت گفتم که با توجه به اطلاعاتی که بدست آوردی امسال چه انرژی هایی برات فعاله!!!\n\n"
                    "🔹 به‌علاوه، یک پاکسازی ویژه «نگهبان نور» که  برای رفع دعا و طلسم و جادو و چشم زخم  و انرژی حسادت در سال ۲۰۲۶ باید حتما انجامش بدی چون تو رو دربرابر همه این خطر ها محافظت میکنه.\n\n"
                    "اگه هنوز وارد کانال تلگرام نشدی و این آموزش‌ها رو نداری،👇\n"
                    "همین الان روی لینک زیر بزن و وارد شو\n"
                    "تا از این اطلاعات ارزشمند جا نمونی\n\n"
                    "https://t.me/fereshte2026\n\n"
                    "سوالی هم داشتی از آیدی زیر بپرس 👇🏼\n"
                    "@fereshtehelp"
                ),
                parse_mode="HTML",
            )    
            

            with Session(engine) as session:
                statement = select(Zodiac).where(Zodiac.user_id == user_id)
                user = session.exec(statement).first()
                if user:
                    count_visit = user.count_visit + 1
                else:
                    count_visit = 1
                    
            
            insert_to_zodiac_table(
                engine=engine,
                user_id=user_id,
                birth_date=f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}",
                chinese_sign=chinese_sign,
                chinese_element=chinese_element,
                count_visit=count_visit
            )

            user_zodiac_data.pop(user_id, None)
            markup = dashboard_keyboard()
            await bot.send_message(
                chat_id=user_id,
                text=f"اینجا چندتا گزینه وجود داره که میتونی انتخاب کنی:",
                reply_markup=markup
            )
            await bot.answer_callback_query(callback_query_id=call.id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=TEXT_ZODIAC_MAX_VISIT
            )



@bot.message_handler(commands=['user_count'])
async def get_user_count(message):
    with Session(engine) as session:
        statement = select(User)
        users = session.exec(statement).all()
        user_count = len(users)
    await bot.send_message(
        message.chat.id,
        f"تعداد کل افراد: {user_count}"
    )


@bot.message_handler(commands=["send"])
async def handle_broadcast(message):
    print(message.from_user.id)
    if message.from_user.id not in [7690029281, 52260445, 917104518]:
        await bot.reply_to(message, "🚫 You are not authorized to use this command.")
        return
    
    if message.reply_to_message:
        parts = message.text.split()
        city_keywords = parts[1:] if len(parts) > 1 else []
        
        from_chat_id = message.chat.id
        message_id = message.reply_to_message.message_id
        
        await bot.send_message(from_chat_id, "ارسال پیام آغاز شد!")
        
        send_count = await forward_message_to_users(
            engine=engine,
            bot=bot,
            from_chat_id=from_chat_id,
            message_id=message_id,
            cities=city_keywords
        )
        
        if city_keywords:
            cities_str = "، ".join(city_keywords)
            await bot.reply_to(
                message,
                f" پیام به {send_count} نفر با شهرهای شامل: {cities_str} ارسال شد ✅",
            )
        else:
            await bot.reply_to(
                message,
                f" پیام بدون فیلتر شهر، برای {send_count} نفر ارسال شد ✅",
            )        
    else:
        await bot.send_message(message.chat.id, "برای ارسال پیام گروهی، باید روی آن پیام ریپلای کرده و دستور /send را بنویسی.")

    # msg_text = message.text[len("/broadcast") :].strip()
    # if msg_text:
    #     await send_message_to_all_users(engine=engine, table='user', bot=bot, message_text=msg_text)
    #     await bot.reply_to(message, "✅ Message sent to all users!")
    # else:
    #     await bot.reply_to(message, "⚠️ Please provide a message after /broadcast.")

# Add command for reset MAX_CALCULATION
@bot.message_handler(commands=["reset"])
async def reset(message):
    
    if message.from_user.id != 7690029281:
        await bot.reply_to(message, "🚫 You are not authorized to use this command.")
        return
    
    try:        
        with Session(engine) as session:
            session.exec(update(Kua).values(count_visit=0))
            session.exec(update(Zodiac).values(count_visit=0))
            session.commit()
        await bot.reply_to(message, "✅ All count_visit values have been reset to zero.")
        
    except Exception as e:
        await bot.reply_to(message, f"❌ An error occurred: {str(e)}")
    


@bot.message_handler(commands=['send_message'])
async def send_message(message):
    with Session(engine) as session:
        result = session.exec(text(f"SELECT * FROM user"))
        results = [(row.user_id, row.given_name, row.city) for row in result.fetchall()]
    n = 0
    for item in results:
        try:
            user_id, given_name, city = item
            message_text = (
                f"سلام {given_name} عزیز!\n"
                "فرشته خسروی هستم.\n"
                "برای ارتباط بهتر و همراهی همیشگیتون\n"
                "حتما\n"
                "✅کانال ایتا و\n"
                "✅کانال روبیکا و\n"
                "✅ کانال تلگرام\n"
                "✅شماره پشتیبانی\n\n"
                "رو داشته باشید\n\n"
                "لینک کانال ایتا👇\n"
                "https://eitaa.com/halekhob999\n\n"
                "لینک کانال روبیکا👇\n"
                "https://rubika.ir/helekhobmalkhob\n\n"
                "لینک کانال تلگرام 👇\n"
                "https://t.me/helekhobmalkhob\n\n"
                "شماره پشتیبانی مستقیم👇\n"
                "09364998675\n"
                "آقای روان بخش\n\n"
                "به امید روزای خوب 💚"
                "دوستت دارم/فرشته💚\n\n\n"
                "(اگر میخوایید پیامی برامون بفرستید روی دکمه زیر بزنین و پیامتون رو یکجا ارسال کنین)\n\n"
            )
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✉️ ارسال پیام", callback_data=f"reply_{user_id}")
            )
            
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await asyncio.sleep(0.3)
            n += 1
        except apihelper.ApiException as e:
            print(f"Error for {user_id}: {e}")
        except Exception as e:
            print(f"Unexpected error for {user_id}: {e}")
            
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"Send Message to {n} Users!"
    )



@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
async def handle_reply_request(call):
    user_id = call.from_user.id

    with Session(engine) as session:
        state = session.get(UserReplyState, user_id)
        if state:
            state.is_waiting = True
        else:
            state = UserReplyState(user_id=user_id, is_waiting=True)
            session.add(state)
        session.commit()

    await bot.send_message(
        chat_id=user_id,
        text="📝 حالا پیامت رو برام بنویس\nمن می‌خونمش با دقت ❤️"
    )


@bot.message_handler(func=lambda msg: True)
async def handle_user_reply(msg):
    user_id = msg.from_user.id
    with Session(engine) as session:
        state = session.get(UserReplyState, user_id)
        if state and state.is_waiting:
            state.is_waiting = False
            session.commit()

            await bot.send_message(
                chat_id=6561974562,
                text=f"📩 پیام جدید از {msg.from_user.full_name} (ID: {user_id}):\n\n{msg.text}",
            )

            await bot.send_message(
                chat_id=user_id,
                text="پیامت رسید ✅ ممنونم ازت ❤️"
            )





    


# ------------------------------------------------------------------------------ #
#                              Handle /FengShui Test Command
# ------------------------------------------------------------------------------ #

POLL_QUESTIONS = [
    {
        "q": "❓ سوال اول:\nمن ...",
        "a": [
            {"text": "شغلم را دوست دارم و درآمد خوبی دارم", "score": 9},
            {"text": "شغلم را دوست دارم ولی درآمد کمی دارم", "score": 5},
            {"text": "شغل و درآمدم را دوست ندارم و میخواهم آن را عوض کنم", "score": 3},
        ]
    },
    {
        "q": "❓ سوال دوم:\nمن تقریبا ...",
        "a": [
            {"text": "هر ماه سفر میروم", "score": 9},
            {"text": "سالی 2 الی 3 بار سفر میروم", "score": 5},
            {"text": "چند ساله سفر نرفته ام", "score": 3},
        ]
    },
    {
        "q": "❓ سوال سوم:\nوضعیت روابط عاشقانه ...",
        "a": [
            {"text": "متاهلم (در رابطه هستم)/ رابطه عالی دارم", "score": 9},
            {"text": "متاهلم (در رابطه هستم)/ رابطه خوبی ندارم.", "score": 4},
            {"text": "مجردم / کسی توی زندگیم نیست", "score": 7},
        ]
    },
    {
        "q": "❓ سوال چهارم:\nوضعیت سلامتی و بیماری ...",
        "a": [
            {"text": "خدارو شکر که از سلامتی کافی برخوردارم", "score": 9},
            {"text": "هر ماه اعضای خانواده من مریض میشوند", "score": 4},
            {"text": "متاسفانه درگیر بیماری طولانی هستم", "score": 3},
        ]
    },
    {
        "q": "❓ سوال پنجم:\nوضعیت روابط با نزدیکان ...",
        "a": [
            {"text": "با دوستان و فامیل رابطه عالی دارم", "score": 7},
            {"text": "متاسفانه با نزدیکانم مشکل دادگاهی دارم", "score": 5},
            {"text": "تنهایم و با کسی رابطه خوبی ندارم", "score": 4},
        ]
    },
    {
        "q": "❓ سوال ششم:\nوضعیت فرزندان ...",
        "a": [
            {"text": "فرزندان خوب و مطیعی دارم", "score": 8},
            {"text": "فرزندان پرخاشگر و بی توجه به تحصیل دارم", "score": 3},
            {"text": "میخواهم مادر شوم", "score": 3},
            {"text": "فرزند ندارم", "score": 5},
        ]
    },
    {
        "q": "❓ سوال هفتم:\nدرآمد من ...",
        "a": [
            {"text": "زیر 10 میلیون است", "score": 2},
            {"text": "بین 10 تا 20 میلیون است", "score": 6},
            {"text": "25 میلیون به بالا است", "score": 9},
        ]
    },
    {
        "q": "❓ سوال هشتم:\nزمانیکه تصمیم به انجام کاری میگیرید، آن کار چطور پیش میرود؟",
        "a": [
            {"text": "آسان و راحت به نتیجه مورد نظر میرسد", "score": 7},
            {"text": "خیلی سخت نتیجه میگیرم یا رهایش میکنم", "score": 3},
        ]
    },
    {
        "q": "❓ سوال نهم:\nدرب ورودی شما در کدام جهت از نقشه خانه شما قرار گرفته است؟",
        "a": [
            {"text": "شمال", "score": 1},
            {"text": "شمال شرقی", "score": 1},
            {"text": "شرق", "score": 1},
            {"text": "جنوب شرقی", "score": 1},
            {"text": "جنوب", "score": 1},
            {"text": "جنوب غربی", "score": 1},
            {"text": "غرب", "score": 1},
            {"text": "شمال غربی", "score": 1},
            {"text": "نمیدانم", "score": 1},
        ]
    },
    {
        "q": "❓ سوال دهم:\nآشپزخانه شما در کدام جهت از نقشه خانه شما قرار گرفته است؟",
        "a": [
            {"text": "شمال", "score": 1},
            {"text": "شمال شرقی", "score": 1},
            {"text": "شرق", "score": 1},
            {"text": "جنوب شرقی", "score": 1},
            {"text": "جنوب", "score": 1},
            {"text": "جنوب غربی", "score": 1},
            {"text": "غرب", "score": 1},
            {"text": "شمال غربی", "score": 1},
            {"text": "نمیدانم", "score": 1},
        ]
    },
    {
        "q": "❓ سوال یازدهم:\nسرویس بهداشتی / حمام شما در کدام جهت از نقشه خانه شما قرار گرفته است؟",
        "a": [
            {"text": "شمال", "score": 1},
            {"text": "شمال شرقی", "score": 1},
            {"text": "شرق", "score": 1},
            {"text": "جنوب شرقی", "score": 1},
            {"text": "جنوب", "score": 1},
            {"text": "جنوب غربی", "score": 1},
            {"text": "غرب", "score": 1},
            {"text": "شمال غربی", "score": 1},
            {"text": "نمیدانم", "score": 1},
        ]
    },
    {
        "q": "❓ سوال دوازدهم:\nاتاق زوجین در کدام جهت از نقشه خانه شما قرار گرفته است؟",
        "a": [
            {"text": "شمال", "score": 1},
            {"text": "شمال شرقی", "score": 1},
            {"text": "شرق", "score": 1},
            {"text": "جنوب شرقی", "score": 1},
            {"text": "جنوب", "score": 1},
            {"text": "جنوب غربی", "score": 1},
            {"text": "غرب", "score": 1},
            {"text": "شمال غربی", "score": 1},
            {"text": "نمیدانم", "score": 1},
        ]
    },
    {
        "q": "❓ سوال سیزدهم:\nاتاق فرزند در کدام جهت از نقشه خانه شما قرار گرفته است؟",
        "a": [
            {"text": "شمال", "score": 1},
            {"text": "شمال شرقی", "score": 1},
            {"text": "شرق", "score": 1},
            {"text": "جنوب شرقی", "score": 1},
            {"text": "جنوب", "score": 1},
            {"text": "جنوب غربی", "score": 1},
            {"text": "غرب", "score": 1},
            {"text": "شمال غربی", "score": 1},
            {"text": "نمیدانم", "score": 1},
        ]
    },
    {
        "q": "❓ سوال چهاردهم:\nآیا در منزل شما یک یا همه موارد زیر وجود دارد؟ (راه پله / نور گیر / پاسیو / ستون)",
        "a": [
            {"text": "بله", "score": 1},
            {"text": "خیر", "score": 1},
        ]
    },
]

async def simulate_progress(chat_id, n, text):
    message = await bot.send_message(chat_id, f"{text}: [                    ] 0%")
    for i in range(1, n + 1):
        await asyncio.sleep(0.5)
        progress = int((i / n) * 100)
        bar = '█' * i + ' ' * (n - i)
        await bot.edit_message_text(chat_id=chat_id, message_id=message.message_id,
                                    text=f"{text}[{bar}] {progress}%")
    await bot.delete_message(chat_id=chat_id, message_id=message.message_id)


user_poll_state = {}

@bot.message_handler(commands=['fengshui_test'])
async def start_fengshui_test(message):
    user_id = message.chat.id
    user_poll_state[user_id] = {"current": 0, "answers": []}
    await bot.send_message(
            chat_id=user_id,
            text=(
                "✋ سلام دوست من، سوالات تست زیر رو با دقت و واقعی جواب بده تا تحلیل کنم سطح فرکانس محیط زندگی تو از نظر فنگشویی در چه سطحیه.\n\n"
                "✅✅✅✅✅✅✅\n"
                "این تست اختصاصی توسط تیم فرشته خسروی برای اولین بار در ایران طراحی و اجرا شده است و میتوانید سنجش ارتعاش محیط خود را انجام دهید.\n"
                "✅✅✅✅✅✅✅\n\n"
                "📊 با این تست سطح انرژی منزل  شما بررسی می‌شود و با توجه به نتیجه تست راهکارهایی برای افزایش سطح انرژی به شما داده می‌شود."
                "⚠️ عزیز این تست شامل 14 سوال است. لطفا سعی کنید زیر ده دقیقه تست را انجام دهید.\n\n"
                "🔴 در پاسخ به هر سوال لطفا نزدیکترین جوابی که به ذهنتان رسید را انتخاب کنید.\n\n"
            ),
            parse_mode="HTML",
        )
    await bot.send_message(
            chat_id=user_id,
            text=(
                "📝 بیا شروع کنیم:\n\n"
            ),
            parse_mode="HTML",
        )
    await simulate_progress(user_id, n=10, text="🔄 یکم صبر کن تا سوال‌ها بارگزاری بشه ...\n")
    await send_fengshui_question(user_id)


async def send_fengshui_question(user_id):
    state = user_poll_state.get(user_id)
    if state is None:
        return
    idx = state["current"]
    if idx < len(POLL_QUESTIONS):
        q = POLL_QUESTIONS[idx]
        markup = InlineKeyboardMarkup()
        for i, ans in enumerate(q["a"]):
            markup.add(InlineKeyboardButton(ans["text"], callback_data=f"poll_{idx}_{i}"))
        sent_message = await bot.send_message(user_id, q["q"], reply_markup=markup, parse_mode="HTML")
        state["last_question_message_id"] = sent_message.message_id
    else:
        total = sum(state["answers"])
        await bot.send_message(user_id, f"📢 سوالات تمام شد!")
        await simulate_progress(user_id, n=12, text="🔄 در حال محاسبه امتیاز نهایی ...\n")
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"🗯 امتیاز نهایی شما {total} از 100! 🗯\n\n"
                f"📝 این هم تحلیل تست فنگشویی شما:\n\n"
                f"☹️ امتیاز زیر 40: خیلی بد\n"
                f"😑 امتیاز بین 40 تا 70: وضعیت معمولی\n"
                f"😊 امتیاز بالای 70: عالی\n"
            ),
            parse_mode="HTML",
        )
        
        insert_to_fengshui_score_table(
            engine=engine,
            user_id=user_id,
            score=total
        )

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 ثبت درخواست", callback_data="collect_info"))

        await bot.send_message(
            chat_id=user_id,
            text=(
                "😍 در صورت تمایل میتوانید از فنگشویی توسط خود خانم خسروی  استفاده کنید و فرکانس و انرژی محیط خود را بالا ببرید.\n\n"    
                "✅فنگشویی توسط خود خانم خسروی به صورت حضوری (ظرفیت تا آخر تابستان تکمیل ): متری ۲۰۰ هزار تومان و \n\n"
                "به صورت آنلاین :متری ۱۰۰ هزار تومان\n"
                "🛑یعنی مبلغ برای فنگشویی آنلاین یک خونه ۱۰۰ متری ۱۰ میلیون تومان است.\n\n"
                "در صورت تمایل رزرو فنگشویی خود را انجام دهید‌👇🏼\n"
            ),
            reply_markup=markup,
            parse_mode="HTML"
        )

        await bot.send_message(
            chat_id=user_id,
            text=(
                "سلام 🌱\n",
                "خوشحالم که در مسیر نور و آگاهی قرار داری …\n\n"
                "همین الان وارد کانال زیر بشو  چون به رایگان بهت گفتم که با توجه به اطلاعاتی که بدست آوردی امسال چه انرژی هایی برات فعاله!!!\n\n"
                "🔹 به‌علاوه، یک پاکسازی ویژه «نگهبان نور» که  برای رفع دعا و طلسم و جادو و چشم زخم  و انرژی حسادت در سال ۲۰۲۶ باید حتما انجامش بدی چون تو رو دربرابر همه این خطر ها محافظت میکنه.\n\n"
                "اگه هنوز وارد کانال تلگرام نشدی و این آموزش‌ها رو نداری،👇\n"
                "همین الان روی لینک زیر بزن و وارد شو\n"
                "تا از این اطلاعات ارزشمند جا نمونی\n\n"
                "https://t.me/fereshte2026\n\n"
                "سوالی هم داشتی از آیدی زیر بپرس 👇🏼\n"
                "@fereshtehelp"
            ),
            reply_markup=markup,
            parse_mode="HTML"
        )
        user_poll_state.pop(user_id, None)


user_data_form = {}

@bot.callback_query_handler(func=lambda call: call.data == "collect_info")
async def handle_collect_info(call):
    user_id = call.message.chat.id
    user_data_form[user_id] = {}
    await bot.send_message(user_id, "🧑 لطفا اسم خود را وارد کنید:")

@bot.message_handler(func=lambda message: message.chat.id in user_data_form and "f_name" not in user_data_form[message.chat.id])
async def get_f_name(message):
    user_data_form[message.chat.id]["f_name"] = message.text
    await bot.send_message(message.chat.id, "🧑 لطفا فامیل خود را وارد کنید:")

@bot.message_handler(func=lambda message: message.chat.id in user_data_form and "l_name" not in user_data_form[message.chat.id])
async def get_l_name(message):
    user_data_form[message.chat.id]["l_name"] = message.text
    await bot.send_message(message.chat.id, "📱 لطفا شماره تلفن خود را وارد کنید:")

@bot.message_handler(func=lambda message: message.chat.id in user_data_form and "phone" not in user_data_form[message.chat.id])
async def get_phone(message):
    user_data_form[message.chat.id]["phone"] = message.text
    await bot.send_message(message.chat.id, "🏙 لطفا شهر محل سکونت خود را وارد کنید:")

@bot.message_handler(func=lambda message: message.chat.id in user_data_form and "city" not in user_data_form[message.chat.id])
async def get_city(message):
    user_data_form[message.chat.id]["city"] = message.text
    await bot.send_message(message.chat.id, "🏠 لطفا متراژ خانه خود را وارد کنید:")

@bot.message_handler(func=lambda message: message.chat.id in user_data_form and "metrage" not in user_data_form[message.chat.id])
async def get_metrage(message):
    user_data_form[message.chat.id]["metrage"] = message.text
    await bot.send_message(message.chat.id, "❓ مشکل یا چالشی که دارید را توضیح دهید:")

@bot.message_handler(func=lambda message: message.chat.id in user_data_form and "problem" not in user_data_form[message.chat.id])
async def get_problem(message):
    user_id = message.chat.id
    user_data_form[user_id]["problem"] = message.text

    data = user_data_form.pop(user_id)

    insert_to_fengshui_test_table(
        engine=engine,
        user_id=user_id,
        f_name=data["f_name"],
        l_name=data["l_name"],
        phone=data["phone"],
        city=data["city"],
        metrage=data["metrage"],
        problem=data["problem"]
    )

    await bot.send_message(user_id, "✅ اطلاعات شما با موفقیت ذخیره شد. همکاران ما با شما تماس خواهند گرفت.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("poll_"))
async def handle_poll_answer(call):
    user_id = call.message.chat.id
    state = user_poll_state.get(user_id)
    if not state:
        await bot.answer_callback_query(call.id, "لطفا با /fengshui_test شروع کنید.")
        return
    _, idx, ans_idx = call.data.split("_")
    idx = int(idx)
    ans_idx = int(ans_idx)
    if idx != state["current"]:
        await bot.answer_callback_query(call.id, "این سوال قبلا پاسخ داده شده است.")
        return
    score = POLL_QUESTIONS[idx]["a"][ans_idx]["score"]
    answer_text = POLL_QUESTIONS[idx]["a"][ans_idx]["text"]
    state["answers"].append(score)
    state["current"] += 1
    
    last_msg_id = state.get("last_question_message_id")
    if last_msg_id:
        try:
            await bot.delete_message(chat_id=user_id, message_id=last_msg_id)
        except Exception as e:
            print(f"خطا در حذف پیام: {e}")

    await send_fengshui_question(user_id)
    await bot.answer_callback_query(call.id)
 

# ------------------------------------------------------------------------------ #
#                              Handle /FengShui Test Command
# ------------------------------------------------------------------------------ #




async def main():
    await bot.set_my_description(
        description=(     
            "👋  سلام عشق فرشته 💚😍\n\n"
            "🤖  خیلی خوشحالم که همراه آموزش‌ها بودی. قراره با استفاده از این ربات به صورت رایگان عدد کوا و زودیاک خودت و اعضای خانوادتو محاسبه کنم و بهت بگم تا خیالت از انرژی‌های 2025 راحت باشه.\n\n"
            "🚺📅🚹   کافیه به ترتیب سال / ماه / روز تولدت و جنسیت رو انتخاب کنی تا من بهت بگم عدد شانس و زودیاکت چی هست!\n\n"
            "این ربات قابلیت اینو داره که با پاسخگویی به چند سوال ساده سطح فرکانس و ارتعاش محیطتت رو بسنجه\n\n"
            "💡   برای شروع روی /start بزن!"
        ),
    )
    await bot.set_my_commands(
         commands=[
            BotCommand("start", "صفحه اصلی بات"),
            # BotCommand("mashhad", "ثبت نام سفر مشهد"),
            BotCommand("kua", "عدد شانس (کوا)"),
            BotCommand("zodiac", "محاسبه زودیاک تولد"),
            BotCommand("help", "راهنما"),
            BotCommand("fengshui_test", "تست فنگ شویی"),
         ]
    )
    
    
    
    
    
    
    
    # ADMIN_CHAT_ID = 52260445
    # user_dataaa = defaultdict(dict) 
    # @bot.message_handler(commands=['send'])
    # async def start(message):
    #     await bot.send_message(message.chat.id, "Hello! Please send a picture.")
    
    
    # @bot.message_handler(func=lambda message: message.content_type != 'photo')
    # async def handle_non_photo(message):
    #     print(f"Debug: Non-photo content received. Content type: {message.content_type}")
    #     await bot.send_message(message.chat.id, "Please send only a picture.")
    
       
    # @bot.message_handler(content_types=['photo'])
    # async def handle_photo(message):
    #     user_id = message.chat.id
    #     photo_id = message.photo[-1].file_id  # Get the highest resolution photo

    #     # Store the user's photo data
    #     user_dataaa[user_id]['photo_id'] = photo_id

    #     # Forward the photo to the admin with inline buttons
    #     markup = InlineKeyboardMarkup()
    #     accept_button = InlineKeyboardButton("Accept", callback_data=f"accept:{user_id}")
    #     reject_button = InlineKeyboardButton("Reject", callback_data=f"reject:{user_id}")
    #     markup.add(accept_button, reject_button)

    #     await bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"Photo from user {user_id}", reply_markup=markup)
    #     await bot.send_message(user_id, "Your photo has been sent for review.")
    
    
    
    # @bot.callback_query_handler(func=lambda call: call.data.startswith(('accept', 'reject')))
    # async def handle_decision(call: CallbackQuery):
    #     decision, user_id = call.data.split(":")
    #     user_id = int(user_id)

    #     if decision == "accept":
    #         await bot.send_message(user_id, "Your photo has been accepted. Thank you!")
    #         await bot.answer_callback_query(call.id, "You accepted the photo.")
    #     elif decision == "reject":
    #         await bot.send_message(user_id, "Your photo has been rejected. Please try again.")
    #         await bot.answer_callback_query(call.id, "You rejected the photo.")

    #     # Optionally remove the inline keyboard from the admin's message
    #     await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)   
    
    
    try:
        print("Bot is running ...")
        await bot.polling(non_stop=True)
    except Exception as e:
        print(f"An error occurred: {e}")
        await asyncio.sleep(5)



if __name__ == "__main__":
    asyncio.run(main())
