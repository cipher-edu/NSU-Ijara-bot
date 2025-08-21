
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    role = Column(String, default='User', nullable=False)  # Rollar: User, Admin, Superadmin
    telefon_raqami = Column(String, nullable=True)  # <-- Qo'shildi
    created_at = Column(DateTime, default=datetime.utcnow)

class Listing(Base):
    __tablename__ = 'listings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    shahar = Column(String, nullable=False)
    mahalla = Column(String, nullable=False)
    manzil = Column(String, nullable=False)
    uy_egasining_fish = Column(String, nullable=False)
    telefon_raqami = Column(String, nullable=False)
    ogil_talaba_soni = Column(Integer, default=0)
    qiz_talaba_soni = Column(Integer, default=0)
    holati = Column(String, nullable=False)  # "Uy egasi bilan" / "Uy egasisiz"
    status = Column(String, default='Aktiv emas', nullable=False)  # Status: "Aktiv", "Aktiv emas", "Band"
    qo_shimcha_malumotlar = Column(Text, nullable=True)
    rasmlar = Column(Text, nullable=True) # Rasm file_id'lari JSON string ko'rinishida saqlanadi
    created_by_admin_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    # Yangi maydonlar: yulduzcha baholari va saqlanganlar
    star_1_count = Column(Integer, default=0)
    star_2_count = Column(Integer, default=0)
    star_3_count = Column(Integer, default=0)
    star_4_count = Column(Integer, default=0)
    star_5_count = Column(Integer, default=0)
    saved_by_users = Column(Text, nullable=True) # JSON list: user_id lar
    
    admin = relationship("User")

class FAQ(Base):
    __tablename__ = 'faqs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    savol = Column(Text, nullable=False)
    javob = Column(Text, nullable=False)
    created_by_admin_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    admin = relationship("User")

# Ma'lumotlar bazasini yaratish va ulanish
POSTGRES_USER = os.getenv('POSTGRES_USER', 'students_rent_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'students_rent_pass')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'students_rent')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)