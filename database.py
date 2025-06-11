import sqlite3

def init_db():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY, name TEXT, price REAL, description TEXT, image_url TEXT, video_url TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY, user_id INTEGER, product_id INTEGER, quantity INTEGER, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, phone_number TEXT, is_verified INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (id INTEGER PRIMARY KEY, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Check and add video_url column if missing
    c.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in c.fetchall()]
    if 'video_url' not in columns:
        c.execute("ALTER TABLE products ADD COLUMN video_url TEXT")
        print("Added video_url column to products table")
    
    conn.commit()
    conn.close()

def add_product(name, price, description, image_url=None, video_url=None):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, description, image_url, video_url) VALUES (?, ?, ?, ?, ?)",
              (name, price, description, image_url, video_url))
    conn.commit()
    conn.close()

def update_product(product_id, name=None, price=None, description=None, image_url=None, video_url=None):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    updates = []
    values = []
    if name:
        updates.append("name = ?")
        values.append(name)
    if price:
        updates.append("price = ?")
        values.append(price)
    if description:
        updates.append("description = ?")
        values.append(description)
    if image_url:
        updates.append("image_url = ?")
        values.append(image_url)
    if video_url:
        updates.append("video_url = ?")
        values.append(video_url)
    if updates:
        values.append(product_id)
        query = f"UPDATE products SET {', '.join(updates)} WHERE id = ?"
        c.execute(query, values)
        conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def get_products():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return products

def add_order(user_id, product_id, quantity):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("INSERT INTO orders (user_id, product_id, quantity, status) VALUES (?, ?, ?, ?)",
              (user_id, product_id, quantity, 'pending'))
    conn.commit()
    conn.close()

def get_user_orders(user_id):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT o.id, p.name, p.price, o.quantity, o.status, o.created_at FROM orders o JOIN products p ON o.product_id = p.id WHERE o.user_id = ?", (user_id,))
    orders = c.fetchall()
    conn.close()
    return orders

def add_user(user_id, phone_number):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, phone_number, is_verified) VALUES (?, ?, 0)",
              (user_id, phone_number))
    conn.commit()
    conn.close()

def verify_user(user_id):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_news(content):
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("INSERT INTO news (content) VALUES (?)", (content,))
    conn.commit()
    conn.close()

def get_news():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT * FROM news ORDER BY created_at DESC LIMIT 5")
    news = c.fetchall()
    conn.close()
    return news

def get_all_users():
    conn = sqlite3.connect('shop.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    return [user[0] for user in users]