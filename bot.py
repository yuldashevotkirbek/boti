import os
import sqlite3
import random
import string
import logging
from telethon import TelegramClient, events, Button
from telethon.tl.types import InputMediaPhoto, InputMediaUploadedDocument
from dotenv import load_dotenv
from database import init_db, add_product, get_products, add_order, get_user_orders, add_user, verify_user, get_user, update_product, delete_product, add_news, get_news, get_all_users

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
try:
    ADMIN_ID = int(os.getenv('ADMIN_ID'))
except (TypeError, ValueError):
    logger.error("Invalid ADMIN_ID in .env file")
    raise ValueError("ADMIN_ID must be a valid integer")

# Validate environment variables
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("Missing required environment variables: API_ID, API_HASH, or BOT_TOKEN")
    raise ValueError("API_ID, API_HASH, and BOT_TOKEN must be set in environment variables")

# Initialize TelegramClient
client = TelegramClient('bot', int(API_ID), API_HASH, base_logger=logger)

# Initialize database
init_db()

# State management
user_states = {}
STATE_PHONE = 'phone'
STATE_OTP = 'otp'
STATE_ADD_PRODUCT = 'add_product'
STATE_EDIT_PRODUCT = 'edit_product'
STATE_DELETE_PRODUCT = 'delete_product'
STATE_ADD_NEWS = 'add_news'

# Generate OTP
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

# Populate products (sample data with no media for safety)
def populate_products():
    products = [
        ("iPhone 13", 799.99, "Latest iPhone, 128GB", None, None),
        ("Samsung S23", 699.99, "Flagship Samsung phone", None, None),
        ("MacBook Pro", 1299.99, "16GB RAM, 512GB SSD", None, None),
    ]
    for product in products:
        add_product(*product)

# /start command
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    user = get_user(user_id)
    if user and user[2]:  # is_verified
        keyboard = [
            [Button.inline("Products", b"products")],
            [Button.inline("My Orders", b"my_orders")],
            [Button.inline("Profile", b"profile")],
            [Button.inline("News", b"news")]
        ]
        if user_id == ADMIN_ID:
            keyboard.append([Button.inline("Admin Panel", b"admin_panel")])
        await event.reply("Welcome to our shop!", buttons=keyboard)
        logger.info(f"Verified user {user_id} started the bot")
    else:
        user_states[user_id] = {'state': STATE_PHONE}
        await event.reply("Please enter your phone number (e.g., +998901234567):")
        logger.info(f"User {user_id} prompted for phone number")

# Handle text messages (for phone and OTP)
@client.on(events.NewMessage)
async def handle_text(event):
    user_id = event.sender_id
    if user_id not in user_states:
        return
    state = user_states[user_id].get('state')
    text = event.message.text.strip()

    if state == STATE_PHONE:
        if text.startswith('+') and len(text) >= 10:
            add_user(user_id, text)
            otp = generate_otp()
            user_states[user_id] = {'state': STATE_OTP, 'otp': otp, 'phone': text}
            await event.reply(f"OTP sent: {otp} (for demo, shown here). Enter the OTP:")
            logger.info(f"OTP sent to user {user_id}")
        else:
            await event.reply("Invalid phone number. Please use format: +998901234567")
    elif state == STATE_OTP:
        if text == user_states[user_id]['otp']:
            verify_user(user_id)
            del user_states[user_id]
            await event.reply("Verification successful! Use /start to continue.")
            logger.info(f"User {user_id} verified")
        else:
            await event.reply("Invalid OTP. Try again:")
    elif state == STATE_ADD_PRODUCT:
        step = user_states[user_id].get('step', 'name')
        if step == 'name':
            user_states[user_id]['name'] = text
            user_states[user_id]['step'] = 'price'
            await event.reply("Enter product price (e.g., 99.99):")
        elif step == 'price':
            try:
                price = float(text)
                user_states[user_id]['price'] = price
                user_states[user_id]['step'] = 'description'
                await event.reply("Enter product description:")
            except ValueError:
                await event.reply("Invalid price. Enter a number (e.g., 99.99):")
        elif step == 'description':
            user_states[user_id]['description'] = text
            user_states[user_id]['step'] = 'media'
            await event.reply("Send an image or video (or type 'skip' to skip):")
    elif state == STATE_EDIT_PRODUCT:
        product_id = user_states[user_id]['product_id']
        step = user_states[user_id].get('step', 'field')
        if step == 'field':
            if text in ['name', 'price', 'description', 'image', 'video']:
                user_states[user_id]['field'] = text
                user_states[user_id]['step'] = 'value'
                await event.reply(f"Enter new {text} (for price, use number; for image/video, send media or URL):")
            else:
                await event.reply("Invalid field. Choose: name, price, description, image, video")
        elif step == 'value':
            field = user_states[user_id]['field']
            if field == 'price':
                try:
                    value = float(text)
                except ValueError:
                    await event.reply("Invalid price. Enter a number:")
                    return
            else:
                value = text
            update_product(product_id, **{field: value})
            del user_states[user_id]
            await event.reply(f"Product {field} updated!", buttons=[[Button.inline("Back", b"admin_panel")]])
            logger.info(f"Admin {user_id} updated product {product_id} {field}")
    elif state == STATE_DELETE_PRODUCT:
        try:
            product_id = int(text)
            delete_product(product_id)
            del user_states[user_id]
            await event.reply("Product deleted!", buttons=[[Button.inline("Back", b"admin_panel")]])
            logger.info(f"Admin {user_id} deleted product {product_id}")
        except ValueError:
            await event.reply("Invalid product ID. Enter a number:")
    elif state == STATE_ADD_NEWS:
        add_news(text)
        del user_states[user_id]
        users = get_all_users()
        for uid in users:
            try:
                await client.send_message(uid, f"News: {text}")
            except Exception as e:
                logger.error(f"Failed to send news to {uid}: {e}")
        await event.reply("News posted and broadcasted!", buttons=[[Button.inline("Back", b"admin_panel")]])
        logger.info(f"Admin {user_id} posted news: {text}")

# Handle media for product creation
@client.on(events.NewMessage(incoming=True))
async def handle_media(event):
    user_id = event.sender_id
    if user_id not in user_states or user_states[user_id].get('state') != STATE_ADD_PRODUCT:
        return
    if user_states[user_id].get('step') != 'media':
        return
    if event.message.text and event.message.text.lower() == 'skip':
        add_product(
            user_states[user_id]['name'],
            user_states[user_id]['price'],
            user_states[user_id]['description']
        )
        del user_states[user_id]
        await event.reply("Product added!", buttons=[[Button.inline("Back", b"admin_panel")]])
        logger.info(f"Admin {user_id} added product without media")
        return
    if event.message.media:
        try:
            file = await event.message.download_media()
            if event.message.photo:
                add_product(
                    user_states[user_id]['name'],
                    user_states[user_id]['price'],
                    user_states[user_id]['description'],
                    image_url=file
                )
            elif event.message.video:
                add_product(
                    user_states[user_id]['name'],
                    user_states[user_id]['price'],
                    user_states[user_id]['description'],
                    video_url=file
                )
            del user_states[user_id]
            await event.reply("Product added with media!", buttons=[[Button.inline("Back", b"admin_panel")]])
            logger.info(f"Admin {user_id} added product with media")
        except Exception as e:
            logger.error(f"Failed to handle media for user {user_id}: {e}")
            await event.reply("Error processing media. Please try again or type 'skip'.")
            return

# Show products
@client.on(events.CallbackQuery(data=b'products'))
async def show_products(event):
    user = get_user(event.sender_id)
    if not user or not user[2]:
        await event.answer("Please verify your phone number first!")
        return
    products = get_products()
    keyboard = [[Button.inline(f"{p[1]} - ${p[2]}", f"product_{p[0]}")] for p in products]
    keyboard.append([Button.inline("Back", b"back")])
    await event.edit("Select a product:", buttons=keyboard)
    logger.info(f"User {event.sender_id} viewed products")

# Product details
@client.on(events.CallbackQuery(pattern=b'product_.*'))
async def product_details(event):
    try:
        product_id = int(event.data.decode().split('_')[1])
        products = get_products()
        product = next((p for p in products if p[0] == product_id), None)
        if product:
            name, price, description, image_url, video_url = product[1], product[2], product[3], product[4], product[5]
            keyboard = [
                [Button.inline("Add to Cart", f"add_to_cart_{product_id}")],
                [Button.inline("Back", b"products")]
            ]
            media = None
            if image_url and os.path.exists(image_url):
                try:
                    uploaded_file = await client.upload_file(image_url)
                    media = InputMediaUploadedDocument(file=uploaded_file, mime_type='image/jpeg')
                except Exception as e:
                    logger.error(f"Failed to upload image for product {product_id}: {e}")
            elif video_url and os.path.exists(video_url):
                try:
                    uploaded_file = await client.upload_file(video_url)
                    media = InputMediaUploadedDocument(file=uploaded_file, mime_type='video/mp4')
                except Exception as e:
                    logger.error(f"Failed to upload video for product {product_id}: {e}")
            elif image_url and image_url.startswith(('http://', 'https://')):
                media = InputMediaPhoto(image_url)
            elif video_url and video_url.startswith(('http://', 'https://')):
                media = InputMediaUploadedDocument(file=video_url, mime_type='video/mp4')

            await event.edit(
                f"**{name}**\nPrice: ${price}\nDescription: {description}",
                buttons=keyboard,
                file=media
            )
            logger.info(f"User {event.sender_id} viewed product {product_id}")
        else:
            await event.answer("Product not found!")
    except Exception as e:
        logger.error(f"Error in product_details for user {event.sender_id}: {e}")
        await event.answer("Error displaying product. Please try again.")
        await show_products(event)

# Add to cart
@client.on(events.CallbackQuery(pattern=b'add_to_cart_.*'))
async def add_to_cart(event):
    product_id = int(event.data.decode().split('_')[3])
    user_id = event.sender_id
    add_order(user_id, product_id, 1)
    await event.answer("Product added to cart!")
    await show_products(event)
    logger.info(f"User {user_id} added product {product_id} to cart")

# My orders
@client.on(events.CallbackQuery(data=b'my_orders'))
async def my_orders(event):
    user_id = event.sender_id
    user = get_user(user_id)
    if not user or not user[2]:
        await event.answer("Please verify your phone number first!")
        return
    orders = get_user_orders(user_id)
    if not orders:
        await event.edit("You have no orders!", buttons=[[Button.inline("Back", b"back")]])
        return
    text = "Your orders:\n"
    for order in orders:
        text += f"Order #{order[0]}: {order[1]} - ${order[2]} x {order[3]} ({order[4]}) on {order[5]}\n"
    await event.edit(text, buttons=[[Button.inline("Back", b"back")]])
    logger.info(f"User {user_id} viewed their orders")

# User profile
@client.on(events.CallbackQuery(data=b'profile'))
async def profile(event):
    user_id = event.sender_id
    user = get_user(user_id)
    if not user or not user[2]:
        await event.answer("Please verify your phone number first!")
        return
    orders = get_user_orders(user_id)
    text = f"**Profile**\nPhone: {user[1]}\nVerified: Yes\nTotal Orders: {len(orders)}"
    await event.edit(text, buttons=[[Button.inline("Back", b"back")]])
    logger.info(f"User {user_id} viewed their profile")

# News
@client.on(events.CallbackQuery(data=b'news'))
async def show_news(event):
    user = get_user(event.sender_id)
    if not user or not user[2]:
        await event.answer("Please verify your phone number first!")
        return
    news = get_news()
    if not news:
        await event.edit("No news available!", buttons=[[Button.inline("Back", b"back")]])
        return
    text = "Latest News:\n"
    for n in news:
        text += f"{n[2]}: {n[1]}\n"
    await event.edit(text, buttons=[[Button.inline("Back", b"back")]])
    logger.info(f"User {event.sender_id} viewed news")

# Admin panel
@client.on(events.CallbackQuery(data=b'admin_panel'))
async def admin_panel(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("You are not an admin!")
        logger.warning(f"User {event.sender_id} attempted to access admin panel")
        return
    keyboard = [
        [Button.inline("View Orders", b"view_orders")],
        [Button.inline("Add Product", b"add_product")],
        [Button.inline("Edit Product", b"edit_product")],
        [Button.inline("Delete Product", b"delete_product")],
        [Button.inline("Add News", b"add_news")],
        [Button.inline("Back", b"back")]
    ]
    await event.edit("Admin Panel:", buttons=keyboard)
    logger.info(f"Admin {event.sender_id} accessed admin panel")

# View all orders (admin)
@client.on(events.CallbackQuery(data=b'view_orders'))
async def view_orders(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("You are not an admin!")
        return
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT o.id, p.name, p.price, o.quantity, o.status, o.user_id, o.created_at FROM orders o JOIN products p ON o.product_id = p.id")
    orders = c.fetchall()
    conn.close()
    if not orders:
        await event.edit("No orders found!", buttons=[[Button.inline("Back", b"admin_panel")]])
        return
    text = "All orders:\n"
    for order in orders:
        text += f"Order #{order[0]}: {order[1]} - ${order[2]} x {order[3]} ({order[4]}) by User {order[5]} on {order[6]}\n"
    await event.edit(text, buttons=[[Button.inline("Back", b"admin_panel")]])
    logger.info(f"Admin {event.sender_id} viewed all orders")

# Add product (admin)
@client.on(events.CallbackQuery(data=b'add_product'))
async def add_product_start(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("You are not an admin!")
        return
    user_states[event.sender_id] = {'state': STATE_ADD_PRODUCT, 'step': 'name'}
    await event.reply("Enter product name:")
    logger.info(f"Admin {event.sender_id} started adding product")

# Edit product (admin)
@client.on(events.CallbackQuery(data=b'edit_product'))
async def edit_product_start(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("You are not an admin!")
        return
    products = get_products()
    keyboard = [[Button.inline(f"{p[1]} - ${p[2]}", f"edit_select_{p[0]}")] for p in products]
    keyboard.append([Button.inline("Back", b"admin_panel")])
    await event.edit("Select product to edit:", buttons=keyboard)
    logger.info(f"Admin {event.sender_id} started editing product")

@client.on(events.CallbackQuery(pattern=b'edit_select_.*'))
async def edit_product_select(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("You are not an admin!")
        return
    product_id = int(event.data.decode().split('_')[2])
    user_states[event.sender_id] = {'state': STATE_EDIT_PRODUCT, 'product_id': product_id, 'step': 'field'}
    await event.reply("Which field to edit? (name, price, description, image, video)")
    logger.info(f"Admin {event.sender_id} selected product {product_id} for editing")

# Delete product (admin)
@client.on(events.CallbackQuery(data=b'delete_product'))
async def delete_product_start(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("You are not an admin!")
        return
    products = get_products()
    keyboard = [[Button.inline(f"{p[1]} - ${p[2]}", f"delete_select_{p[0]}")] for p in products]
    keyboard.append([Button.inline("Back", b"admin_panel")])
    await event.edit("Select product to delete:", buttons=keyboard)
    logger.info(f"Admin {event.sender_id} started deleting product")

@client.on(events.CallbackQuery(pattern=b'delete_select_.*'))
async def delete_product_select(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("You are not an admin!")
        return
    product_id = int(event.data.decode().split('_')[2])
    user_states[event.sender_id] = {'state': STATE_DELETE_PRODUCT, 'product_id': product_id}
    await event.reply("Enter the product ID to confirm deletion:")
    logger.info(f"Admin {event.sender_id} selected product {product_id} for deletion")

# Add news (admin)
@client.on(events.CallbackQuery(data=b'add_news'))
async def add_news_start(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("You are not an admin!")
        return
    user_states[event.sender_id] = {'state': STATE_ADD_NEWS}
    await event.reply("Enter news content:")
    logger.info(f"Admin {event.sender_id} started adding news")

# Back button
@client.on(events.CallbackQuery(data=b'back'))
async def back(event):
    user = get_user(event.sender_id)
    if not user or not user[2]:
        await event.answer("Please verify your phone number first!")
        return
    keyboard = [
        [Button.inline("Products", b"products")],
        [Button.inline("My Orders", b"my_orders")],
        [Button.inline("Profile", b"profile")],
        [Button.inline("News", b"news")]
    ]
    if event.sender_id == ADMIN_ID:
        keyboard.append([Button.inline("Admin Panel", b"admin_panel")])
    await event.edit("Welcome back!", buttons=keyboard)
    logger.info(f"User {event.sender_id} returned to main menu")

# Main function
async def main():
    try:
        await client.start(bot_token=BOT_TOKEN)
        populate_products()
        logger.info("Bot started successfully")
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise

# Start the bot
if __name__ == '__main__':
    client.loop.run_until_complete(main())