# Senior: check if user has rated a listing
def has_user_rated_listing(listing_id, user_id):
    session = DBSession()
    listing = session.query(Listing).filter(Listing.id == listing_id).first()
    rated = False
    if listing:
        for i in range(1, 6):
            key = f'star_by_users_{i}'
            users_json = getattr(listing, key, None)
            users = json.loads(users_json) if users_json else []
            if user_id in users:
                rated = True
                break
    session.close()
    return rated

def add_star_to_listing(listing_id, user_id, star_count):
    session = DBSession()
    listing = session.query(Listing).filter(Listing.id == listing_id).first()
    if listing and 1 <= star_count <= 5:
        # Check if user has rated this listing with any star value
        user_already_rated = False
        for i in range(1, 6):
            key = f'star_by_users_{i}'
            users_json = getattr(listing, key, None)
            users = json.loads(users_json) if users_json else []
            if user_id in users:
                user_already_rated = True
                break
        if user_already_rated:
            session.close()
            return False
        key = f'star_by_users_{star_count}'
        users_json = getattr(listing, key, None)
        users = json.loads(users_json) if users_json else []
        users.append(user_id)
        setattr(listing, key, json.dumps(users))
        setattr(listing, f'star_{star_count}_count', getattr(listing, f'star_{star_count}_count') + 1)
        session.commit()
        session.close()
        return True
    session.close()
    return False
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Listing, FAQ
from config import SUPERADMIN_IDS
import json
import os
import redis

from dotenv import load_dotenv
load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

POSTGRES_USER = os.getenv('POSTGRES_USER', 'students_rent_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'students_rent_pass')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'students_rent')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine, expire_on_commit=False)

# Foydalanuvchi funksiyalari
def get_or_create_user(user_id, first_name, username):
    # Redisda user keshini tekshiramiz
    cache_key = f"user:{user_id}"
    cached_user = redis_client.get(cache_key)
    if cached_user:
        import pickle
        return pickle.loads(bytes.fromhex(cached_user))
    session = DBSession()
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        role = 'Superadmin' if user_id in SUPERADMIN_IDS else 'User'
        user = User(user_id=user_id, first_name=first_name, username=username, role=role)
        session.add(user)
        session.commit()
    # Redisga userni keshga yozamiz
    try:
        import pickle
        redis_client.set(cache_key, pickle.dumps(user).hex(), ex=3600)
    except Exception:
        pass
    session.close()
    return user

def create_or_update_user(user_id, first_name, username, telefon_raqami):
    session = DBSession()
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user:
        role = 'Superadmin' if user_id in SUPERADMIN_IDS else 'User'
        user = User(user_id=user_id, first_name=first_name, username=username, role=role, telefon_raqami=telefon_raqami)
        session.add(user)
    else:
        user.first_name = first_name
        user.username = username
        user.telefon_raqami = telefon_raqami
    session.commit()
    # Redis keshini yangilash
    try:
        import pickle
        cache_key = f"user:{user_id}"
        redis_client.set(cache_key, pickle.dumps(user).hex(), ex=3600)
    except Exception:
        pass
    session.close()
    return user

def get_user_role(user_id):
    # Redisdan roleni olishga harakat qilamiz
    cache_key = f"user:{user_id}"
    cached_user = redis_client.get(cache_key)
    if cached_user:
        import pickle
        user = pickle.loads(bytes.fromhex(cached_user))
        return user.role if user else None
    session = DBSession()
    user = session.query(User).filter(User.user_id == user_id).first()
    session.close()
    return user.role if user else None

# Admin funksiyalari
def get_admins():
    session = DBSession()
    admins = session.query(User).filter(User.role.in_(['Admin', 'Superadmin'])).all()
    session.close()
    return admins

def set_user_role(user_id, role):
    session = DBSession()
    user = session.query(User).filter(User.user_id == user_id).first()
    if user:
        user.role = role
        session.commit()
        # Redis keshini yangilash
        try:
            import pickle
            cache_key = f"user:{user_id}"
            redis_client.set(cache_key, pickle.dumps(user).hex(), ex=3600)
        except Exception:
            pass
        session.close()
        return True
    session.close()
    return False

import ast
# Xonadon (Listing) funksiyalari
def add_listing(data):
    session = DBSession()
    # Rasmlar list'ini JSON string'ga o'tkazish
    if 'rasmlar' in data and isinstance(data['rasmlar'], list):
        data['rasmlar'] = json.dumps(data['rasmlar'])
    # Saqlanganlar va baholar uchun default qiymatlar
    data.setdefault('star_1_count', 0)
    data.setdefault('star_2_count', 0)
    data.setdefault('star_3_count', 0)
    data.setdefault('star_4_count', 0)
    data.setdefault('star_5_count', 0)
    data.setdefault('saved_by_users', json.dumps([]))
    new_listing = Listing(**data)
    session.add(new_listing)
    session.commit()
    session.close()

# Foydalanuvchi xonadonni saqlaydi
def save_listing_for_user(listing_id, user_id):
    session = DBSession()
    listing = session.query(Listing).filter(Listing.id == listing_id).first()
    if listing:
        saved = json.loads(listing.saved_by_users) if listing.saved_by_users else []
        if user_id not in saved:
            saved.append(user_id)
            listing.saved_by_users = json.dumps(saved)
            session.commit()
            session.close()
            return True
    session.close()
    return False

# Foydalanuvchi xonadonni saqlaganmi?
def is_listing_saved_by_user(listing_id, user_id):
    session = DBSession()
    listing = session.query(Listing).filter(Listing.id == listing_id).first()
    session.close()
    if listing and listing.saved_by_users:
        saved = json.loads(listing.saved_by_users)
        return user_id in saved
    return False

# Foydalanuvchi saqlagan xonadonlar ro'yxati
def get_saved_listings_by_user(user_id):
    session = DBSession()
    listings = session.query(Listing).all()
    session.close()
    return [l for l in listings if l.saved_by_users and user_id in json.loads(l.saved_by_users)]

# Xonadonga yulduzcha baho qo'shish


# Xonadon baholari statistikasi
def get_listing_star_stats(listing):
    return {
        1: listing.star_1_count,
        2: listing.star_2_count,
        3: listing.star_3_count,
        4: listing.star_4_count,
        5: listing.star_5_count
    }

def get_listing_by_id(listing_id):
    session = DBSession()
    listing = session.query(Listing).filter(Listing.id == listing_id).first()
    session.close()
    return listing

def get_listings_by_admin(admin_id):
    session = DBSession()
    listings = session.query(Listing).filter(Listing.created_by_admin_id == admin_id).all()
    session.close()
    return listings

def update_listing_status(listing_id, status):
    session = DBSession()
    listing = session.query(Listing).filter(Listing.id == listing_id).first()
    if listing:
        listing.status = status
        session.commit()
        session.close()
        return True
    session.close()
    return False

def delete_listing(listing_id):
    session = DBSession()
    listing = session.query(Listing).filter(Listing.id == listing_id).first()
    if listing:
        session.delete(listing)
        session.commit()
        session.close()
        return True
    session.close()
    return False

def filter_listings(filters):
    session = DBSession()
    query = session.query(Listing).filter(Listing.status == 'Aktiv')
    
    if filters.get('shahar'):
        query = query.filter(Listing.shahar.ilike(f"%{filters['shahar']}%"))
    if filters.get('jins') == "O'g'il bolalar uchun":
        query = query.filter(Listing.ogil_talaba_soni > 0)
    if filters.get('jins') == "Qiz bolalar uchun":
        query = query.filter(Listing.qiz_talaba_soni > 0)
    if filters.get('holati'):
        query = query.filter(Listing.holati == filters['holati'])
        
    results = query.all()
    session.close()
    return results

# FAQ funksiyalari
def add_faq(savol, javob, admin_id):
    session = DBSession()
    new_faq = FAQ(savol=savol, javob=javob, created_by_admin_id=admin_id)
    session.add(new_faq)
    session.commit()
    session.close()

def get_all_faqs():
    session = DBSession()
    faqs = session.query(FAQ).all()
    session.close()
    return faqs

def delete_faq(faq_id):
    session = DBSession()
    faq = session.query(FAQ).filter(FAQ.id == faq_id).first()
    if faq:
        session.delete(faq)
        session.commit()
        session.close()
        return True
    session.close()
    return False
### 5. `keyboards.py`

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard(role):
    keyboard = [
        ["🔍 Xonadon qidirish"],
        ["❓ Ko'p beriladigan savollar", "☎️ Biz bilan aloqa"]
    ]
    if role in ['Admin', 'Superadmin']:
        keyboard.append(["🔐 Boshqaruv paneli"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_panel_keyboard(role):
    keyboard = [
        ["🏠 Xonadonlarni boshqarish"],
        ["❓ FAQni boshqarish"]
    ]
    if role == 'Superadmin':
        keyboard.append(["👨‍💼 Adminlarni boshqarish"])
    keyboard.append(["⬅️ Bosh menyuga qaytish"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def listings_management_keyboard():
    return ReplyKeyboardMarkup([
        ["➕ Xonadon qo'shish", "📋 Mening e'lonlarim"],
        ["⬅️ Ortga"]
    ], resize_keyboard=True)

def superadmin_panel_keyboard():
    return ReplyKeyboardMarkup([
        ["➕ Admin qo'shish", "➖ Adminni o'chirish"],
        ["📋 Adminlar ro'yxati", "⬅️ Ortga"]
    ], resize_keyboard=True)
    
def faq_management_keyboard():
    return ReplyKeyboardMarkup([
        ["➕ FAQ qo'shish", "🗑 FAQ o'chirish"],
        ["⬅️ Ortga"]
    ], resize_keyboard=True)

# --- Inline Keyboards ---

def listing_controls_keyboard(listing_id, role):
    keyboard = []
    if role in ['Admin', 'Superadmin']:
        keyboard.append([
            InlineKeyboardButton("🔄 Statusni o'zgartirish", callback_data=f"change_status_{listing_id}"),
            InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete_listing_{listing_id}")
        ])
    return InlineKeyboardMarkup(keyboard)

def change_status_keyboard(listing_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Aktiv", callback_data=f"set_status_{listing_id}_Aktiv")],
        [InlineKeyboardButton("❌ Aktiv emas", callback_data=f"set_status_{listing_id}_Aktiv emas")],
        [InlineKeyboardButton("🔒 Band", callback_data=f"set_status_{listing_id}_Band")]
    ])
    
def confirm_deletion_keyboard(item_type, item_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"confirm_delete_{item_type}_{item_id}"),
            InlineKeyboardButton("❌ Yo'q, bekor qilish", callback_data=f"cancel_delete")
        ]
    ])

# --- Qidiruv uchun tugmalar ---

def search_gender_keyboard():
    return ReplyKeyboardMarkup([
        ["O'g'il bolalar uchun"],
        ["Qiz bolalar uchun"],
        ["Farqi yo'q"],
        ["⬅️ Bekor qilish"]
    ], resize_keyboard=True, one_time_keyboard=True)

def search_condition_keyboard():
    return ReplyKeyboardMarkup([
        ["Uy egasi bilan"],
        ["Uy egasisiz"],
        ["Farqi yo'q"],
        ["⬅️ Bekor qilish"]
    ], resize_keyboard=True, one_time_keyboard=True)

def has_pressed_rating_button(listing_id, user_id):
    pressed_key = f"rating_pressed:{listing_id}:{user_id}"
    return bool(redis_client.get(pressed_key))

def should_show_rating_button(listing_id, user_id):
    # Hide rating button if user has rated or pressed the button before
    if has_user_rated_listing(listing_id, user_id):
        return False
    if has_pressed_rating_button(listing_id, user_id):
        return False
    return True

def mark_rating_button_pressed(listing_id, user_id):
    # Call this when user interacts with the rating button (even if they don't rate)
    pressed_key = f"rating_pressed:{listing_id}:{user_id}"
    redis_client.set(pressed_key, "1", ex=86400)  # expires in 1 day

def has_pressed_save_button(listing_id, user_id):
    pressed_key = f"save_pressed:{listing_id}:{user_id}"
    return bool(redis_client.get(pressed_key))

def should_show_save_button(listing_id, user_id):
    # Hide save button if user has saved or pressed the button before
    if is_listing_saved_by_user(listing_id, user_id):
        return False
    if has_pressed_save_button(listing_id, user_id):
        return False
    return True

def mark_save_button_pressed(listing_id, user_id):
    # Call this when user interacts with the save button (even if they don't save)
    pressed_key = f"save_pressed:{listing_id}:{user_id}"
    redis_client.set(pressed_key, "1", ex=86400)  # expires in 1 day