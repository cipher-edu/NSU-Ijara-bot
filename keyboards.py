# keyboards.py

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard(role):
    """Foydalanuvchi rolidan kelib chiqib asosiy menyu tugmalarini qaytaradi."""
    keyboard = [
        ["🔍 Xonadon qidirish"],
        ["⭐ Saqlangan e'lonlar"],
        ["❓ Ko'p beriladigan savollar", "☎️ Biz bilan aloqa"]
    ]
    if role in ['Admin', 'Superadmin']:
        keyboard.append(["🔐 Boshqaruv paneli"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_panel_keyboard(role):
    """Admin va Superadmin uchun boshqaruv paneli tugmalari."""
    keyboard = [
        ["🏠 Xonadonlarni boshqarish"],
        ["❓ FAQni boshqarish"]
    ]
    if role == 'Superadmin':
        keyboard.append(["👨‍💼 Adminlarni boshqarish"])
    keyboard.append(["⬅️ Bosh menyuga qaytish"]) # STANDARTLASHTIRILDI
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def listings_management_keyboard():
    """Xonadonlarni boshqarish menyusi."""
    return ReplyKeyboardMarkup([
        ["➕ Xonadon qo'shish", "📋 Mening e'lonlarim"],
        ["⬅️ Ortga"] # STANDARTLASHTIRILDI
    ], resize_keyboard=True)

def superadmin_panel_keyboard():
    """Faqat Superadmin uchun adminlarni boshqarish menyusi."""
    return ReplyKeyboardMarkup([
        ["➕ Admin qo'shish", "➖ Adminni o'chirish"],
        ["📋 Adminlar ro'yxati", "⬅️ Ortga"] # STANDARTLASHTIRILDI
    ], resize_keyboard=True)
    
def faq_management_keyboard():
    """FAQ (savol-javoblar) bo'limini boshqarish menyusi."""
    return ReplyKeyboardMarkup([
        ["➕ FAQ qo'shish", "🗑 FAQ o'chirish"],
        ["⬅️ Ortga"] # STANDARTLASHTIRILDI
    ], resize_keyboard=True)

# --- Qidiruv uchun to'g'rilangan tugmalar ---

def search_gender_keyboard():
    """Qidiruvda jinsni tanlash tugmalari (HANDLERGA MOSLASHTIRILDI)."""
    return ReplyKeyboardMarkup([
        ["O'g'il bolalar uchun"],
        ["Qiz bolalar uchun"],
        ["Farqi yo'q"],
        ["⬅️ Bekor qilish"]
    ], resize_keyboard=True, one_time_keyboard=True)

def search_condition_keyboard():
    """Qidiruvda xonadon holatini tanlash tugmalari (HANDLERGA MOSLASHTIRILDI)."""
    return ReplyKeyboardMarkup([
        ["Uy egasi bilan"],
        ["Uy egasisiz"],
        ["Farqi yo'q"],
        ["⬅️ Bekor qilish"]
    ], resize_keyboard=True, one_time_keyboard=True)


# --- Inline Keyboards ---

def listing_controls_keyboard(listing_id, role, is_saved=False, user_id=None):
    keyboard = []
    if role == 'User':
        save_text = "⭐ Saqlash" if not is_saved else "⭐ Saqlangan"
        keyboard.append([InlineKeyboardButton(save_text, callback_data=f"save_listing_{listing_id}")])
        from database import has_user_rated_listing
        if user_id is not None and not has_user_rated_listing(listing_id, user_id):
            keyboard.append([InlineKeyboardButton("⭐ Baholash", callback_data=f"rate_listing_{listing_id}")])
    if role in ['Admin', 'Superadmin']:
        keyboard.append([
            InlineKeyboardButton("🔄 Statusni o'zgartirish", callback_data=f"set_status_{listing_id}_choose"),
            InlineKeyboardButton("🗑 O'chirish", callback_data=f"confirm_delete_listing_{listing_id}")
        ])
    return InlineKeyboardMarkup(keyboard)
def change_status_keyboard(listing_id):
    """Xonadon statusini o'zgartirish uchun inline tugmalar."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Aktiv", callback_data=f"set_status_{listing_id}_Aktiv")],
        [InlineKeyboardButton("❌ Aktiv emas", callback_data=f"set_status_{listing_id}_Aktiv emas")],
        [InlineKeyboardButton("🔒 Band", callback_data=f"set_status_{listing_id}_Band")]
    ])

def confirm_deletion_keyboard(item_type, item_id):
    """O'chirishni tasdiqlash uchun inline tugmalar."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"confirm_delete_{item_type}_{item_id}"),
            InlineKeyboardButton("❌ Yo'q, bekor qilish", callback_data=f"cancel_delete")
        ]
    ])

def rate_stars_keyboard(listing_id):
    """Baholash uchun 1-5 yulduzcha tugmalari."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ 1", callback_data=f"star_{listing_id}_1"),
         InlineKeyboardButton("⭐ 2", callback_data=f"star_{listing_id}_2"),
         InlineKeyboardButton("⭐ 3", callback_data=f"star_{listing_id}_3"),
         InlineKeyboardButton("⭐ 4", callback_data=f"star_{listing_id}_4"),
         InlineKeyboardButton("⭐ 5", callback_data=f"star_{listing_id}_5")]
    ])