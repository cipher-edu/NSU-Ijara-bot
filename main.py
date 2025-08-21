from telegram.ext import ApplicationBuilder, CommandHandler
from config import BOT_TOKEN
from handlers import (
    start, contact, show_faqs,
    admin_panel, back_to_main_menu,
    listings_management, my_listings, back_to_admin_panel,
    superadmin_panel, list_admins,
    faq_management,
    add_listing_conversation,
    search_conversation,
    add_admin_conversation,
    remove_admin_conversation,
    add_faq_conversation,
    delete_faq_conversation,
    button_callback,
    registration_conversation  # <-- Qo'shildi
)

def main():
    # Application yaratish
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation handlers
    application.add_handler(registration_conversation)  # <-- Qo'shildi
    application.add_handler(add_listing_conversation)
    application.add_handler(search_conversation)
    application.add_handler(add_admin_conversation)
    application.add_handler(remove_admin_conversation)
    application.add_handler(add_faq_conversation)
    application.add_handler(delete_faq_conversation)
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))

    # Message handlers (matnli tugmalar uchun)
    application.add_handler(contact)
    application.add_handler(show_faqs)
    application.add_handler(admin_panel)
    application.add_handler(back_to_main_menu)
    application.add_handler(listings_management)
    application.add_handler(my_listings)
    from handlers import saved_listings_handler
    application.add_handler(saved_listings_handler)
    application.add_handler(back_to_admin_panel)
    application.add_handler(superadmin_panel)
    application.add_handler(list_admins)
    application.add_handler(faq_management)

    # CallbackQueryHandler (inline tugmalar uchun)
    from handlers import button_callback
    application.add_handler(button_callback)
    
    # Botni ishga tushirish
    print("Bot ishga tushdi...")
    application.run_polling()

if __name__ == '__main__':
    main()