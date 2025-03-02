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
    extract_chinese_year,
    calculate_kua_number,
    calculate_zodiac_animal,
    send_join_channel_button,
    send_message_to_all_users,
    forward_message_to_all_users,
    decade_buttons,
    year_buttons,
    month_buttons,
    day_buttons,
    gender_buttons,
    check_visit_count,
    check_register
)
from models import User, Kua, Zodiac, Mashhad
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
            text="ارسال شماره", 
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

@bot.callback_query_handler(func=lambda call: call.data in ["mashhad_button", "kua_button", "zodiac_button", "help_button", "start_button"])
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
@bot.message_handler(commands=['mashhad'])
async def mashhad_command(message):
    user_id = message.chat.id 
    if await user_channel_check(
        engine=engine,
        table=Mashhad,
        bot=bot,
        message=message,
        user_id=user_id,
        max_visit=MAX_VISIT,
        channels=CHANNELS
    ):
        if check_register(
            engine=engine,
            table=Mashhad,
            user_id=user_id,
        ):
            await bot.send_message(
                chat_id=message.chat.id,
                text=(
                    "قراره یک نفر برنده سفر مشهد و زیارت حرم امام رضا (ع) بشه.\n\n"
                    "اطلاعاتی که در ادامه ازت خواسته میشه رو با دقت وارد کن تا ثبت نام اولیه‌ات تکمیل بشه.\n\n"
                ),
                parse_mode="HTML",
            )
            user_mashhad_data[message.chat.id] = {
                "state": "awaiting_name_mashhad",
            }
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"لطفا اسم و فامیل خودت را به فارسی این زیر بنویس:",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text="شما قبلا ثبت نام اولیه را انجام داده‌اید، نیاز به ثبت نام مجدد نمی‌باشد!"
            )


@bot.message_handler(func=lambda message: user_mashhad_data.get(message.chat.id, {}).get("state") == "awaiting_name_mashhad")
async def handle_mashhad_name(message):
    name = message.text
    user_mashhad_data[message.chat.id] = {
        "state": "awaiting_mashhad_city",
        "name": name,
    }
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"لطفا شهر خودت را به فارسی این زیر بنویس:",
    )


@bot.message_handler(func=lambda message: user_mashhad_data.get(message.chat.id, {}).get("state") == "awaiting_mashhad_city")
async def handle_mashhad_city(message):
    user_id = message.chat.id
    name = user_mashhad_data[message.chat.id]["name"]
    city = message.text
    print("Start: ", user_id)
    print("Name: ", name)
    print("City: ", city)
    print("End: ", user_id)
    insert_to_mashhad_table(
        engine=engine,
        user_id=user_id,
        name=name,
        city=city
    )
    del user_mashhad_data[message.chat.id]
    markup = dashboard_keyboard()
    await bot.send_message(
        chat_id=message.chat.id,
        text=(
            "شرایط این جایزه رو کامل بخون\n"
            "قراره یک نفر مهمون خودم بیاد مشهد تا بریم زیارت امام رضا 🌷\n\n"
            "چله ژورنال ثروت :\n"
            "( کوچ 40 روزه )\n\n"
            "💥40 کُد روزانه\n"
            "💥40 روز شکرگزاری\n"
            "💥40 روز باور فراوانی انرژی\n"
            "ذهنی ، روحی ، جسمی ، محیط\n"
            "( برگزاری در کانال خصوصی تلگرام و روبیکا )\n\n"
            "🎁 هدیه ویژه : مدیتیشن پول \n"
            "100 نفر اول\n\n"
            "🎁🧳یک نفر برنده سفر مشهد و زیارت حرم امام رضا 💚🙏\n\n"
            "🔺🔺🔺🔺کافیه توی این دوره شرکت کنی تا توی قرعه کشی سفر مشهد شانست رو امتحان کنی !\n\n"
            "⏰️ثبت نام : از 15 بهمن \n"
            "❗️فقط برای 300 نفر \n"
            "✔️قیمت دوره : 1/280 تومان \n\n"
            "🛑ظرفیت خیلی محدوده\n"
            "اگه میخوای پیش ثبت نام کنی \n"
            "به این آیدی پیام بده 👇🏼\n\n"
            "@fereshtehelp"
        ),
        parse_mode="HTML",
        reply_markup=markup
    )


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
            
            # Send Kua Number Result
            file_path = os.path.abspath(f"./data/img/kua_number_{kua_number}.png")
            if not os.path.exists(file_path):
                print("File not found:", file_path)
            else:
                print("File founded:", file_path)
            with open(file_path, "rb") as photo:
                print("File opened successfully", file_path)
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=f"عدد کوا شما «{kua_number}» می‌باشد!",
                )  
                    
            # Send Kua Number Result
            file_path_voice = os.path.abspath(f"./data/مهم.m4a")
            if not os.path.exists(file_path_voice):
                print("File not found:", file_path_voice)
            else:
                print("File founded:", file_path_voice)
            with open(file_path_voice, "rb") as voice:
                print("File opened successfully", file_path_voice)
                await bot.send_audio(
                    chat_id=user_id,
                    audio=voice,
                    caption=f"پاکسازی قبل ۲۹ اسفند",
                    timeout=60
                )         
            kn = str(kua_number)
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "اول این ویس بالا رو گوش بده ☝️\n\n"
                    "بعد بر اساس عنصر شخصیت پاکسازیت رو انجام بده.\n\n"
                    f"🔺 عدد شانس شما: {kn}\n"
                    f"🔺 عنصر وجودی شما: {kua_element[kn]["element"]}\n"
                    f"{kua_element[kn]["description"]}\n\n"
                    "پنجشنبه ۹ اسفند\n"
                    "یادت باشه\n"
                    "میخوام با هفت سین ثروتساز سورپرایزت کنم\n\n"
                    "اگه سوالی داشتی به آیدی زیر پیام بده\n"
                    "@fereshtehelp\n"      
                    "👆👆👆👆\n"      
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

                    # Send Kua Number Result
            file_path_voice = os.path.abspath(f"./data/اطلاعیه_مهم.mp4")
            if not os.path.exists(file_path_voice):
                print("File not found:", file_path_voice)
            else:
                print("File founded:", file_path_voice)
            with open(file_path_voice, "rb") as voice:
                print("File opened successfully", file_path_voice)
                await bot.send_audio(
                    chat_id=user_id,
                    audio=voice,
                    caption=f"اطلاعیه بسیار مهم! حتما گوش بدید.",
                    timeout=60
                )


            await bot.send_message(
                chat_id=user_id,
                text=(
                    "اگه میخوای با استفاده از اطلاعاتی که کسب کردی سال 2025 که سال مار هست و با سرعت همه چی اتفاق میافته! تو هم با سرعت به سمت پیشرفت و درآمد قدم بگذاری !\n\n"
                    "❌❌❌❌\n\n"
                    "۲۷ دی ماه\n"
                    "ساعت ۱۱:۱۱\n"
                    "ظرفیت ثبت نام دوره ستارگان رو برای ۵۰۰ نفر باز میکنم \n"
                    "بجای ۳ میلیون میتونی این دوره رو با مبلغ ۸۸۸ هزار تومان تهیه کنی .\n\n"      
                    "❌کلمه ثبت نام رو به آیدی زیر بفرست👇🏼\n\n"
                    "@fereshtehelp\n"      
                    "👆👆👆👆\n"      
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

@bot.message_handler(commands=['sql'])
async def get_user_count(message):
    if message.text == "/sql":
        name = "given_name"
    else:
        name = message.text.replace("/sql ", "")
    try:
        with Session(engine) as session:
            result = session.exec(text(f"SELECT {name} FROM user"))
            results = [row[0] for row in result.fetchall()]
            results_text = "\n".join(results) + "\n"
    except:
        results_text = "دستور اشتباه!"
        
    await bot.send_message(
        chat_id=message.chat.id,
        text=results_text
    )

@bot.message_handler(commands=['send_message'])
async def send_message(message):
    with Session(engine) as session:
        result = session.exec(text(f"SELECT user_id FROM user"))
        results = [row[0] for row in result.fetchall()]
    message_text = (
        "🌟ثبت نام هفت سین ثروتساز شروع شد🌷\n"
        "۳۰۰ نفر اول ۳۰ کُد روزانه فروردین ۱۴۰۴\n"
        "تکنیک لحظه تحویل سال\n"
        "پاکسازی مخصوص خونه تکونی\n\n"
        "بعلت مسدود شدن شماره کارت ها بدلیل حجم ثبت نامی ها\n\n"
        "۲۴ ساعت دیگه ثبت نام تمدید شد."
    )
    n = 0
    for chat_id in results:
        try:
            file_path = os.path.abspath(f"./data/Poster.jpg")
            with open(file_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=message_text,
                    parse_mode="HTML",
                )
            n += 1
            time.sleep(0.2)
        except apihelper.ApiException as e:
            print(f"Error for {chat_id}: {e}")
        except Exception as e:
            print(f"Unexpected error for {chat_id}: {e}")
            
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"Send Message to {n} Users!"
    )

@bot.message_handler(commands=["broadcast"])
async def handle_broadcast(message):
    if message.from_user.id != 7690029281:
        await bot.reply_to(message, "🚫 You are not authorized to use this command.")
        return
    
    if message.reply_to_message:
        from_chat_id = message.chat.id
        message_id = message.reply_to_message.message_id
        await forward_message_to_all_users(engine=engine, table='user', bot=bot, from_chat_id=from_chat_id, message_id=message_id)
        bot.send_message(from_chat_id, "Message has been forwarded to all users.")
    else:
        bot.send_message(message.chat.id, "Please reply to the message you want to broadcast with /broadcast.")

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
    
    




async def main():
    await bot.set_my_description(
        description=(     
            "👋  سلام عشق فرشته 💚😍\n\n"
            "🤖  خیلی خوشحالم که همراه آموزش‌ها بودی. قراره با استفاده از این ربات به صورت رایگان عدد کوا و زودیاک خودت و اعضای خانوادتو محاسبه کنم و بهت بگم تا خیالت از انرژی‌های 2025 راحت باشه.\n\n"
            "🚺📅🚹   کافیه به ترتیب سال / ماه / روز تولدت و جنسیت رو انتخاب کنی تا من بهت بگم عدد شانس و زودیاکت چی هست!\n\n"
            "💡   برای شروع روی /start بزن!"
        ),
    )
    await bot.set_my_commands(
         commands=[
            BotCommand("start", "صفحه اصلی بات"),
            BotCommand("mashhad", "ثبت نام سفر مشهد"),
            BotCommand("kua", "عدد شانس (کوا)"),
            BotCommand("zodiac", "محاسبه زودیاک تولد"),
            BotCommand("help", "راهنما"),
            # BotCommand("send", "راهنما"),
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
