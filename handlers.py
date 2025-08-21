# handlers.py

import json
import html  # HTML belgilarni escape qilish uchun
from telegram import Update, InputMediaPhoto, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode

# Loyihadagi boshqa fayllardan kerakli funksiya va o'zgarchilarni import qilish
import database as db
import keyboards as kb

# ConversationHandler uchun holatlar (states)
(
    # Xonadon qo'shish holatlari
    SHAHAR, MAHALLA, MANZIL, FISH, TEL, OGIL_SONI, QIZ_SONI, HOLATI, QOSHIMCHA, RASMLAR,
    
    # Qidiruv holatlari
    SEARCH_GENDER, SEARCH_CONDITION,
    
    # Admin boshqaruvi holatlari
    ADD_ADMIN_ID, REMOVE_ADMIN_ID,
    
    # FAQ boshqaruvi holatlari
    ADD_FAQ_SAVOL, ADD_FAQ_JAVOB, DELETE_FAQ_ID
) = range(17)


# --- Yordamchi Funksiyalar ---

def escape(text: str) -> str:
    """Matndagi maxsus HTML belgilarini qochirish uchun yordamchi funksiya."""
    return html.escape(str(text))

def format_listing_message(listing):
    """Xonadon ma'lumotlarini chiroyli va ajratilgan dizaynda matnga o'giradi, baholar statistikasi bilan."""
    rasmlar_soni = len(json.loads(listing.rasmlar)) if listing.rasmlar else 0
    star_stats = db.get_listing_star_stats(listing)
    stars_text = "\n".join([
        f"{'⭐'*i} soni: <b>{star_stats[i]}</b>" for i in range(1,6)
    ])
    return (
        f"🏠 <b>Xonadon ID: {listing.id}</b>\n"
        f"📍 <b>Manzil:</b> {escape(listing.shahar)}, {escape(listing.mahalla)} mahallasi, {escape(listing.manzil)}\n"
        f"👤 <b>Uy egasi:</b> {escape(listing.uy_egasining_fish)}\n"
        f"📞 <b>Telefon:</b> <code>{escape(listing.telefon_raqami)}</code>\n"
        f"🚹 <b>O'g'il bolalar uchun joy:</b> {listing.ogil_talaba_soni} ta | "
        f"🚺 <b>Qiz bolalar uchun joy:</b> {listing.qiz_talaba_soni} ta\n"
        f"📋 <b>Holati:</b> {escape(listing.holati)}\n"
        f"ℹ️ <b>Qo'shimcha ma'lumot:</b> {escape(listing.qo_shimcha_malumotlar)}\n"
        f"🖼 <b>Rasmlar soni:</b> {rasmlar_soni} ta\n"
        f"📊 <b>Status:</b> <i>{escape(listing.status)}</i>\n"
        f"<b>Baholar statistikasi:</b>\n{stars_text}"
    )
# --- Inline tugmalar uchun yangi handlerlar ---
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

async def save_listing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    listing_id = int(query.data.split('_')[2])
    success = db.save_listing_for_user(listing_id, user_id)
    await query.answer("Saqlangan!" if success else "Allaqachon saqlangan")
    listing = db.get_listing_by_id(listing_id)
    role = db.get_user_role(user_id)
    is_saved = db.is_listing_saved_by_user(listing_id, user_id)
    await query.edit_message_text(
        format_listing_message(listing),
        parse_mode=ParseMode.HTML,
    reply_markup=kb.listing_controls_keyboard(listing_id, role, is_saved, query.from_user.id)
    )

async def rate_listing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    listing_id = int(query.data.split('_')[2])
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=kb.rate_stars_keyboard(listing_id))

async def star_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    parts = query.data.split('_')
    listing_id = int(parts[1])
    star_count = int(parts[2])
    from database import has_user_rated_listing
    if has_user_rated_listing(listing_id, user_id):
        await query.answer("Siz avval bu elonga baho bergansiz", show_alert=True)
        return
    success = db.add_star_to_listing(listing_id, user_id, star_count)
    await query.answer("Baholandi!" if success else "Xatolik yuz berdi")
    listing = db.get_listing_by_id(listing_id)
    role = db.get_user_role(user_id)
    is_saved = db.is_listing_saved_by_user(listing.id, user_id)
    await query.edit_message_text(
        format_listing_message(listing),
        parse_mode=ParseMode.HTML,
        reply_markup=kb.listing_controls_keyboard(listing_id, role, is_saved, query.from_user.id)
    )
# --- Asosiy Buyruqlar va Menyular ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    /start buyrug'i uchun javob beruvchi funksiya.
    Telefon raqami orqali ro'yxatdan o'tish faqat yangi oddiy foydalanuvchilar uchun.
    """
    user = update.effective_user
    # Avval userni bazaga qo'shamiz yoki olamiz
    db_user = db.get_or_create_user(user.id, user.first_name, user.username)
    role = db_user.role if hasattr(db_user, "role") else db.get_user_role(user.id)
    # Har bir yangi amal oldidan klaviaturani tozalash
    await update.message.reply_text(
        "Botga xush kelibsiz!",
        reply_markup=ReplyKeyboardRemove()
    )
    # Faqat oddiy foydalanuvchi va telefon raqami yo'q bo'lsa, ro'yxatdan o'tkazamiz
    if role == "User" and (not hasattr(db_user, "telefon_raqami") or not db_user.telefon_raqami):
        kb_phone = ReplyKeyboardMarkup(
            [[{"text": "📱 Telefon raqamni yuborish", "request_contact": True}]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await update.message.reply_text(
            "Ro'yxatdan o'tish uchun telefon raqamingizni yuboring:",
            reply_markup=kb_phone
        )
        return TEL
    else:
        await update.message.reply_text(
            f"Assalomu alaykum, {escape(user.first_name)}!\n"
            "Navoiy davlat universiteti tomonidan yaratilingan talabalarning ijara honadon topish botiga xush kelibsiz!",
            reply_markup=kb.main_menu_keyboard(role)
        )
        return ConversationHandler.END

async def get_tel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Foydalanuvchi telefon raqamini yuborganda ro'yxatdan o'tkazadi.
    """
    user = update.effective_user
    contact = update.message.contact
    if contact and contact.user_id == user.id and contact.phone_number:
        phone = contact.phone_number
        db.create_or_update_user(user.id, user.first_name, user.username, phone)
        role = db.get_user_role(user.id)
        await update.message.reply_text(
            "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Asosiy menyu:",
            reply_markup=kb.main_menu_keyboard(role)
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Telefon raqam yuborilmadi yoki o'zingizning kontaktni yuboring. Iltimos, '📱 Telefon raqamni yuborish' tugmasini bosing.",
            reply_markup=ReplyKeyboardRemove()
        )
        return TEL

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """'Biz bilan aloqa' tugmasi uchun."""
    await update.message.reply_text(
        "📞 <b>Biz bilan aloqa</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>Admin:</b> <a href='https://t.me/oybek_abduraimov'>@oybek_abduraimov</a>\n"
        "☎️ <b>Telefon:</b> <code>+998 99 7564934</code>\n"
        "📧 <b>Email:</b> <code>ciphereduuz@gmail.com</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Savollaringiz bo'lsa, bemalol murojaat qiling!",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=ReplyKeyboardRemove()
    )

async def show_faqs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """'Ko'p beriladigan savollar' tugmasi uchun."""
    faqs = db.get_all_faqs()
    if not faqs:
        await update.message.reply_text("Hozircha savol-javoblar mavjud emas.")
        return
    
    message = "❓ <b>Ko'p Beriladigan Savollar</b>\n\n"
    for faq in faqs:
        message += f"<b>Savol:</b> {escape(faq.savol)}\n"
        message += f"<b>Javob:</b> {escape(faq.javob)}\n\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

# --- Boshqaruv Paneli Navigatsiyasi ---

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin panelini ko'rsatadi."""
    role = db.get_user_role(update.effective_user.id)
    if role not in ['Admin', 'Superadmin']:
        return
    await update.message.reply_text(
        "Boshqaruv paneliga xush kelibsiz!",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "Panel:",
        reply_markup=kb.admin_panel_keyboard(role)
    )

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bosh menyuga qaytaradi."""
    role = db.get_user_role(update.effective_user.id)
    await update.message.reply_text(
        "Bosh menyu.",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "Menyu:",
        reply_markup=kb.main_menu_keyboard(role)
    )

async def listings_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xonadonlarni boshqarish menyusini ko'rsatadi."""
    await update.message.reply_text(
        "Xonadonlarni boshqarish bo'limi.",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "Boshqaruv:",
        reply_markup=kb.listings_management_keyboard()
    )
    
async def back_to_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin paneliga qaytaradi."""
    role = db.get_user_role(update.effective_user.id)
    await update.message.reply_text(
        "Boshqaruv paneli.",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "Panel:",
        reply_markup=kb.admin_panel_keyboard(role)
    )

# --- Xonadon Qo'shish Jarayoni (ConversationHandler) ---

async def add_listing_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xonadon qo'shish jarayonini boshlaydi."""
    context.user_data['listing'] = {}
    context.user_data['listing']['rasmlar'] = []
    await update.message.reply_text("Yangi xonadon qo'shish boshlandi.\n\nIltimos, xonadon joylashgan shaharni kiriting:")
    return SHAHAR

async def get_shahar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['listing']['shahar'] = update.message.text
    await update.message.reply_text("Mahallani kiriting:")
    return MAHALLA

async def get_mahalla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['listing']['mahalla'] = update.message.text
    await update.message.reply_text("To'liq manzilni kiriting (ko'cha, uy, xona):")
    return MANZIL
    
async def get_manzil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['listing']['manzil'] = update.message.text
    await update.message.reply_text("Uy egasining F.I.SH'ini kiriting:")
    return FISH

async def get_fish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['listing']['uy_egasining_fish'] = update.message.text
    await update.message.reply_text("Uy egasining telefon raqamini kiriting:")
    return TEL

async def get_tel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['listing']['telefon_raqami'] = update.message.text
    await update.message.reply_text("O'g'il bolalar uchun nechta joy bor? (raqamda kiriting)")
    return OGIL_SONI

async def get_ogil_soni(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['listing']['ogil_talaba_soni'] = int(update.message.text)
        await update.message.reply_text("Qiz bolalar uchun nechta joy bor? (raqamda kiriting)")
        return QIZ_SONI
    except ValueError:
        await update.message.reply_text("Iltimos, son kiriting.")
        return OGIL_SONI

async def get_qiz_soni(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['listing']['qiz_talaba_soni'] = int(update.message.text)
        await update.message.reply_text("Xonadon holatini tanlang:", reply_markup=kb.search_condition_keyboard())
        return HOLATI
    except ValueError:
        await update.message.reply_text("Iltimos, son kiriting.")
        return QIZ_SONI

async def get_holati(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text in ["Uy egasi bilan", "Uy egasisiz"]:
        context.user_data['listing']['holati'] = text
        await update.message.reply_text("Xonadon haqida qo'shimcha ma'lumotlarni kiriting (sharoitlari va h.k.).", reply_markup=kb.admin_panel_keyboard(db.get_user_role(update.effective_user.id)))
        return QOSHIMCHA
    else:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.")
        return HOLATI

async def get_qoshimcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['listing']['qo_shimcha_malumotlar'] = update.message.text
    await update.message.reply_text("Endi xonadon rasmlarini yuboring (bir nechta yuborish mumkin). Tugatgach, 'Tugatdim' tugmasini bosing.", reply_markup=ReplyKeyboardMarkup([["Tugatdim"]], resize_keyboard=True, one_time_keyboard=True))
    return RASMLAR

async def get_rasmlar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_id = update.message.photo[-1].file_id
    context.user_data['listing']['rasmlar'].append(photo_id)
    return RASMLAR

async def end_listing_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Jarayonni yakunlaydi va ma'lumotlarni bazaga saqlaydi."""
    listing_data = context.user_data['listing']
    listing_data['created_by_admin_id'] = update.effective_user.id
    db.add_listing(listing_data)
    await update.message.reply_text("✅ Rahmat! Xonadon muvaffaqiyatli qo'shildi.", reply_markup=kb.listings_management_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Har qanday jarayonni bekor qiladi."""
    role = db.get_user_role(update.effective_user.id)
    await update.message.reply_text("Jarayon bekor qilindi.", reply_markup=kb.admin_panel_keyboard(role))
    context.user_data.clear()
    return ConversationHandler.END

# --- Mening E'lonlarim ---

async def my_listings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adminning o'zi qo'shgan e'lonlarini ko'rsatadi."""
    admin_id = update.effective_user.id
    user_id = update.effective_user.id
    listings = db.get_listings_by_admin(admin_id)
    if not listings:
        await update.message.reply_text("Siz hali xonadon qo'shmagansiz.")
        return
    await update.message.reply_text("Siz qo'shgan xonadonlar ro'yxati:")
    for listing in listings:
        message = format_listing_message(listing)
        photo_ids = json.loads(listing.rasmlar) if listing.rasmlar else []
        role = db.get_user_role(user_id)
        is_saved = db.is_listing_saved_by_user(listing.id, user_id)
        if photo_ids:
            # Barcha suratlarni media group sifatida yuborish
            media_group = []
            for idx, pid in enumerate(photo_ids):
                if idx == 0:
                    media_group.append(InputMediaPhoto(media=pid, caption=message, parse_mode=ParseMode.HTML))
                else:
                    media_group.append(InputMediaPhoto(media=pid))
            await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)
            # Boshqaruv tugmasini alohida yuborish
            await update.message.reply_text(
                f"Xonadon ID: {listing.id} uchun boshqaruv:",
                reply_markup=kb.listing_controls_keyboard(listing.id, role, is_saved, user_id)
            )
        else:
            await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=kb.listing_controls_keyboard(listing.id, role, is_saved, user_id))

# --- Xonadon Qidirish Jarayoni (ConversationHandler) ---

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Qidiruv jarayonini boshlaydi."""
    context.user_data['search_filters'] = {}
    await update.message.reply_text("Qidiruv uchun talabalar jinsini tanlang:", reply_markup=kb.search_gender_keyboard())
    return SEARCH_GENDER

async def search_get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    jins = update.message.text
    if jins != "Farqi yo'q":
        context.user_data['search_filters']['jins'] = jins
    await update.message.reply_text("Xonadon holatini tanlang:", reply_markup=kb.search_condition_keyboard())
    return SEARCH_CONDITION

async def search_get_condition_and_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    holati = update.message.text
    if holati != "Farqi yo'q":
        context.user_data['search_filters']['holati'] = holati
    results = db.filter_listings(context.user_data['search_filters'])
    user_id = update.effective_user.id
    role = db.get_user_role(user_id)
    await update.message.reply_text(f"🔍 Qidiruv natijalari ({len(results)} ta topildi):", reply_markup=kb.main_menu_keyboard(role))
    if not results:
        await update.message.reply_text("Afsuski, sizning so'rovingiz bo'yicha xonadonlar topilmadi.")
    else:
        for listing in results:
            message = format_listing_message(listing)
            photo_ids = json.loads(listing.rasmlar) if listing.rasmlar else []
            role = db.get_user_role(user_id)
            is_saved = db.is_listing_saved_by_user(listing.id, user_id)
            if photo_ids:
                # Barcha suratlarni media group sifatida yuborish
                media_group = []
                for idx, pid in enumerate(photo_ids):
                    if idx == 0:
                        media_group.append(InputMediaPhoto(media=pid, caption=message, parse_mode=ParseMode.HTML))
                    else:
                        media_group.append(InputMediaPhoto(media=pid))
                await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)
                await update.message.reply_text(
                    f"Xonadon ID: {listing.id} uchun baholash:",
                    reply_markup=kb.listing_controls_keyboard(listing.id, role, is_saved, user_id)
                )
            else:
                await update.message.reply_text(
                    message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb.listing_controls_keyboard(listing.id, role, is_saved, user_id)
                )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Qidiruvni bekor qilish."""
    role = db.get_user_role(update.effective_user.id)
    await update.message.reply_text("Qidiruv bekor qilindi.", reply_markup=kb.main_menu_keyboard(role))
    context.user_data.clear()
    return ConversationHandler.END

# --- Superadmin Funksiyalari ---

async def superadmin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Adminlarni boshqarish bo'limi.", reply_markup=kb.superadmin_panel_keyboard())

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Yangi admin qo'shish uchun uning Telegram ID raqamini yuboring yoki undan biror xabar forward qiling.")
    return ADD_ADMIN_ID

async def get_admin_id_and_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin qo'shish uchun ID yoki forward qilingan xabarni qabul qiladi."""
    user_id = None

    # YANGI USUL: forward_origin orqali tekshirish
    if hasattr(update.message, "forward_origin") and update.message.forward_origin:
        if hasattr(update.message.forward_origin, "sender_user") and update.message.forward_origin.sender_user:
            user_id = update.message.forward_origin.sender_user.id
    else:
        try:
            user_id = int(update.message.text)
        except (ValueError, TypeError):
            await update.message.reply_text("Noto'g'ri ID kiritildi. Iltimos, raqam kiriting yoki xabar forward qiling.")
            return ADD_ADMIN_ID

    if not user_id:
        await update.message.reply_text("Foydalanuvchi IDsi topilmadi. Iltimos, faqat foydalanuvchidan xabar forward qiling.")
        return ADD_ADMIN_ID

    success = db.set_user_role(user_id, 'Admin')
    if success:
        await update.message.reply_text(f"✅ Foydalanuvchi ({user_id}) muvaffaqiyatli admin etib tayinlandi.")
    else:
        await update.message.reply_text(f"❌ Xatolik: Foydalanuvchi ({user_id}) topilmadi. U botdan kamida bir marta foydalangan bo'lishi kerak.")

    await update.message.reply_text("Adminlarni boshqarish bo'limi.", reply_markup=kb.superadmin_panel_keyboard())
    return ConversationHandler.END

async def remove_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admins = db.get_admins()
    admin_list = "O'chirish uchun admin ID sini kiriting:\n\n"
    for admin in admins:
        if admin.role == 'Admin':
            admin_list += f"👤 {escape(admin.first_name)} (<code>{admin.user_id}</code>)\n"
    
    await update.message.reply_text(admin_list, parse_mode=ParseMode.HTML)
    return REMOVE_ADMIN_ID

async def get_admin_id_and_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = int(update.message.text)
        success = db.set_user_role(user_id, 'User')
        if success:
            await update.message.reply_text(f"✅ Admin ({user_id}) huquqlari muvaffaqiyatli olib tashlandi.")
        else:
            await update.message.reply_text(f"❌ Xatolik: Bunday ID raqamli admin topilmadi.")
    except ValueError:
        await update.message.reply_text("Noto'g'ri ID kiritildi. Iltimos, raqam kiriting.")
        return REMOVE_ADMIN_ID
    
    return ConversationHandler.END

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admins = db.get_admins()
    message = "👨‍💼 <b>Adminlar ro'yxati</b>\n\n"
    for admin in admins:
        username = f"@{escape(admin.username)}" if admin.username else "Mavjud emas"
        message += f"<b>Ism:</b> {escape(admin.first_name)}\n"
        message += f"<b>Username:</b> {username}\n"
        message += f"<b>ID:</b> <code>{admin.user_id}</code>\n"
        message += f"<b>Rol:</b> {escape(admin.role)}\n"
        message += "---------------------\n"
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

# --- FAQ Boshqaruvi ---
async def faq_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("FAQ bo'limini boshqarish.", reply_markup=kb.faq_management_keyboard())

async def add_faq_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Yangi savolni kiriting:")
    return ADD_FAQ_SAVOL

async def get_faq_savol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['faq_savol'] = update.message.text
    await update.message.reply_text("Endi shu savolga javobni kiriting:")
    return ADD_FAQ_JAVOB

async def get_faq_javob_and_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    savol = context.user_data['faq_savol']
    javob = update.message.text
    admin_id = update.effective_user.id
    db.add_faq(savol, javob, admin_id)
    await update.message.reply_text("✅ Yangi savol-javob muvaffaqiyatli qo'shildi.")
    context.user_data.clear()
    return ConversationHandler.END

async def delete_faq_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    faqs = db.get_all_faqs()
    if not faqs:
        await update.message.reply_text("O'chirish uchun savollar mavjud emas.", reply_markup=kb.faq_management_keyboard())
        return ConversationHandler.END
    
    message = "O'chirish uchun savol ID sini kiriting:\n\n"
    for faq in faqs:
        message += f"<b>ID: {faq.id}</b> - Savol: {escape(faq.savol[:50])}...\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    return DELETE_FAQ_ID

async def get_faq_id_and_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        faq_id = int(update.message.text)
        success = db.delete_faq(faq_id)
        if success:
            await update.message.reply_text(f"✅ ID {faq_id} bo'lgan savol-javob o'chirildi.")
        else:
            await update.message.reply_text("❌ Bunday ID raqamli savol topilmadi.")
    except ValueError:
        await update.message.reply_text("Noto'g'ri ID. Iltimos, raqam kiriting.")
        return DELETE_FAQ_ID
    
    return ConversationHandler.END

# --- Inline Tugmalar Uchun Handler ---

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    action = data[0]
    if action == 'change' and data[1] == 'status':
        listing_id = int(data[2])
        # Agar xabar rasm bo'lsa, edit_message_caption, matn bo'lsa, edit_message_text
        if query.message.photo:
            await query.edit_message_caption(
                caption="Yangi statusni tanlang:",
                reply_markup=kb.change_status_keyboard(listing_id)
            )
        else:
            await query.edit_message_text(
                "Yangi statusni tanlang:",
                reply_markup=kb.change_status_keyboard(listing_id)
            )
    elif action == 'set' and data[1] == 'status':
        listing_id = int(data[2])
        new_status = data[3]
        db.update_listing_status(listing_id, new_status)
        listing = db.get_listing_by_id(listing_id)
        # Agar xabar rasm bo'lsa, edit_message_caption, matn bo'lsa, edit_message_text
        if query.message.photo:
            await query.edit_message_caption(
                caption=format_listing_message(listing),
                parse_mode=ParseMode.HTML,
                reply_markup=kb.listing_controls_keyboard(listing.id, 'Admin')
            )
        else:
            await query.edit_message_text(
                format_listing_message(listing),
                parse_mode=ParseMode.HTML,
                reply_markup=kb.listing_controls_keyboard(listing.id, 'Admin')
            )
    elif action == 'delete' and data[1] == 'listing':
        listing_id = int(data[2])
        await query.message.reply_text(
            f"❓ Rostdan ham ID {listing_id} bo'lgan xonadonni o'chirmoqchimisiz?",
            reply_markup=kb.confirm_deletion_keyboard('listing', listing_id)
        )
    elif action == 'confirm' and data[1] == 'delete':
        item_type = data[2]
        item_id = int(data[3])
        if item_type == 'listing':
            db.delete_listing(item_id)
            await query.edit_message_text(f"✅ Xonadon (ID: {item_id}) muvaffaqiyatli o'chirildi.")
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id - 1)
    elif action == 'cancel' and data[1] == 'delete':
        await query.edit_message_text("O'chirish bekor qilindi.")


# --- Handlerlarni yig'ish ---

# ConversationHandler'lar
registration_conversation = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        TEL: [MessageHandler(filters.CONTACT, get_tel_registration)]
    },
    fallbacks=[]
)

add_listing_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ Xonadon qo'shish$"), add_listing_start)],
    states={
        SHAHAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_shahar)],
        MAHALLA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mahalla)],
        MANZIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_manzil)],
        FISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fish)],
        TEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tel)],
        OGIL_SONI: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ogil_soni)],
        QIZ_SONI: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_qiz_soni)],
        HOLATI: [MessageHandler(filters.Regex("^(Uy egasi bilan|Uy egasisiz)$"), get_holati)],
        QOSHIMCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_qoshimcha)],
        RASMLAR: [
            MessageHandler(filters.PHOTO, get_rasmlar),
            MessageHandler(filters.Regex("^Tugatdim$"), end_listing_add)
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_conversation)]
)

search_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^🔍 Xonadon qidirish$"), search_start)],
    states={
        SEARCH_GENDER: [MessageHandler(filters.Regex("^(O'g'il bolalar uchun|Qiz bolalar uchun|Farqi yo'q)$"), search_get_gender)],
        SEARCH_CONDITION: [MessageHandler(filters.Regex("^(Uy egasi bilan|Uy egasisiz|Farqi yo'q)$"), search_get_condition_and_show)]
    },
    fallbacks=[MessageHandler(filters.Regex("^⬅️ Bekor qilish$"), cancel_search)]
)

add_admin_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ Admin qo'shish$"), add_admin_start)],
    states={
        ADD_ADMIN_ID: [MessageHandler(filters.TEXT | filters.FORWARDED, get_admin_id_and_add)]
    },
    fallbacks=[CommandHandler('cancel', cancel_conversation)]
)

remove_admin_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➖ Adminni o'chirish$"), remove_admin_start)],
    states={
        REMOVE_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_admin_id_and_remove)]
    },
    fallbacks=[CommandHandler('cancel', cancel_conversation)]
)

add_faq_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ FAQ qo'shish$"), add_faq_start)],
    states={
        ADD_FAQ_SAVOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_faq_savol)],
        ADD_FAQ_JAVOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_faq_javob_and_add)]
    },
    fallbacks=[CommandHandler('cancel', cancel_conversation)]
)

delete_faq_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^🗑 FAQ o'chirish$"), delete_faq_start)],
    states={
        DELETE_FAQ_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_faq_id_and_delete)]
    },
    fallbacks=[CommandHandler('cancel', cancel_conversation)]
)


# Oddiy Message Handlerlar (tugmalar uchun)

contact = MessageHandler(filters.Regex("^☎️ Biz bilan aloqa$"), contact)
show_faqs = MessageHandler(filters.Regex("^❓ Ko'p beriladigan savollar$"), show_faqs)
admin_panel = MessageHandler(filters.Regex("^🔐 Boshqaruv paneli$"), admin_panel)
back_to_main_menu = MessageHandler(filters.Regex("^⬅️ Bosh menyuga qaytish$"), back_to_main_menu)
listings_management = MessageHandler(filters.Regex("^🏠 Xonadonlarni boshqarish$"), listings_management)
my_listings = MessageHandler(filters.Regex("^📋 Mening e'lonlarim$"), my_listings)
back_to_admin_panel = MessageHandler(filters.Regex("^⬅️ Ortga$"), back_to_admin_panel)
superadmin_panel = MessageHandler(filters.Regex("^👨‍💼 Adminlarni boshqarish$"), superadmin_panel)
list_admins = MessageHandler(filters.Regex("^📋 Adminlar ro'yxati$"), list_admins)
faq_management = MessageHandler(filters.Regex("^❓ FAQni boshqarish$"), faq_management)

# Saqlangan e'lonlar handler
async def saved_listings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    listings = db.get_saved_listings_by_user(user_id)
    if not listings:
        await update.message.reply_text("Sizda saqlangan e'lonlar yo'q.")
        return
    await update.message.reply_text("Siz saqlagan xonadonlar ro'yxati:")
    for listing in listings:
        message = format_listing_message(listing)
        photo_ids = json.loads(listing.rasmlar) if listing.rasmlar else []
        role = db.get_user_role(user_id)
        is_saved = db.is_listing_saved_by_user(listing.id, user_id)
        if photo_ids:
            media_group = []
            for idx, pid in enumerate(photo_ids):
                if idx == 0:
                    media_group.append(InputMediaPhoto(media=pid, caption=message, parse_mode=ParseMode.HTML))
                else:
                    media_group.append(InputMediaPhoto(media=pid))
            await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)
            await update.message.reply_text(
                f"Xonadon ID: {listing.id} uchun boshqaruv:",
                reply_markup=kb.listing_controls_keyboard(listing.id, role, is_saved, user_id)
            )
        else:
            await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=kb.listing_controls_keyboard(listing.id, role, is_saved, user_id))

saved_listings_handler = MessageHandler(filters.Regex("^⭐ Saqlangan e'lonlar$"), saved_listings)


from telegram.ext import CallbackQueryHandler

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    action = data[0]
    if action == 'save' and data[1] == 'listing':
        user_id = query.from_user.id
        listing_id = int(data[2])
        success = db.save_listing_for_user(listing_id, user_id)
        listing = db.get_listing_by_id(listing_id)
        role = db.get_user_role(user_id)
        is_saved = db.is_listing_saved_by_user(listing_id, user_id)
        await query.edit_message_text(
            format_listing_message(listing),
            parse_mode=ParseMode.HTML,
            reply_markup=kb.listing_controls_keyboard(listing_id, role, is_saved, query.from_user.id)
        )
    elif action == 'rate' and data[1] == 'listing':
        listing_id = int(data[2])
        await query.edit_message_reply_markup(reply_markup=kb.rate_stars_keyboard(listing_id))
    elif action == 'star':
        user_id = query.from_user.id
        listing_id = int(data[1])
        star_count = int(data[2])
        success = db.add_star_to_listing(listing_id, user_id, star_count)
        listing = db.get_listing_by_id(listing_id)
        role = db.get_user_role(user_id)
        is_saved = db.is_listing_saved_by_user(listing_id, user_id)
        await query.edit_message_text(
            format_listing_message(listing),
            parse_mode=ParseMode.HTML,
            reply_markup=kb.listing_controls_keyboard(listing_id, role, is_saved, query.from_user.id)
        )
    elif action == 'set' and data[1] == 'status':
        listing_id = int(data[2])
        if data[3] == 'choose':
            # Status tanlash uchun tugmalar
            await query.edit_message_reply_markup(reply_markup=kb.change_status_keyboard(listing_id))
        else:
            new_status = data[3]
            db.update_listing_status(listing_id, new_status)
            listing = db.get_listing_by_id(listing_id)
            role = db.get_user_role(query.from_user.id)
            is_saved = db.is_listing_saved_by_user(listing_id, query.from_user.id)
            if getattr(query.message, 'photo', None):
                await query.edit_message_caption(
                    caption=format_listing_message(listing),
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb.listing_controls_keyboard(listing_id, role, is_saved, query.from_user.id)
                )
            else:
                await query.edit_message_text(
                    format_listing_message(listing),
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb.listing_controls_keyboard(listing_id, role, is_saved, query.from_user.id)
                )
    elif action == 'confirm' and data[1] == 'delete' and data[2] == 'listing':
        item_id = int(data[3])
        db.delete_listing(item_id)
        await query.edit_message_text(f"✅ Xonadon (ID: {item_id}) muvaffaqiyatli o'chirildi.")
    elif action == 'cancel' and data[1] == 'delete':
        await query.edit_message_text("O'chirish bekor qilindi.")

button_callback = CallbackQueryHandler(button_callback)