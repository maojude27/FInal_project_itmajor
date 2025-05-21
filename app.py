from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, re
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# -------------------- Flask Setup --------------------
app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------- Database Helper --------------------
def get_db_connection():
    conn = sqlite3.connect('food_ordering.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_all_categories():
    conn = get_db_connection()
    categories = conn.execute("SELECT category_id, name FROM categories").fetchall()
    conn.close()
    return categories

# -------------------- Initialize Database --------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE NOT NULL,
            contact TEXT,
            address TEXT,
            password TEXT NOT NULL,
            role TEXT,
            profile_image TEXT DEFAULT '1.png'
        )
    ''')

    # Restaurants
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            restaurant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            location TEXT,
            contact TEXT
        )
    ''')

    # Categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    ''')

    # Menu Items
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            category_id INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,
            image TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(category_id),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id)
        )
    ''')

    # Orders
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            payment_id INTEGER,
            delivery_id INTEGER,
            total_amount INTEGER,
            order_status TEXT,
            order_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # Order Details
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_details (
            detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            item_id INTEGER,
            quantity INTEGER,
            subtotal INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        )
    ''')

    # Payments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            amount INTEGER,
            payment_method TEXT,
            payment_status TEXT,
            date TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    ''')

    # Delivery
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS delivery (
            delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            driver_name TEXT,
            delivery_status TEXT,
            estimated_time TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    ''')

    # Reviews
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_id INTEGER,
        rating INTEGER,
        comment TEXT,
        date TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (item_id) REFERENCES menu_items(item_id),
        UNIQUE(user_id, item_id)  -- Ensures only 1 review per user per item
    )
''')

    # Notifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # Cart
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        )
    ''')

    # Default Admin
    cursor.execute("SELECT * FROM users WHERE email = 'admin@example.com'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash("admin123!")
        cursor.execute('''
            INSERT INTO users (name, email, contact, address, password, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Admin', 'admin@example.com', '0000000000', 'Admin HQ', hashed_pw, 'admin'))
        print("✅ Default admin created: admin@example.com / admin123!")

    conn.commit()
    conn.close()

# -------------------- Basic Pages --------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

# -------------------- Auth Routes --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        if len(password) < 6 or not re.search(r'[A-Z]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Password must be at least 6 characters, include an uppercase letter and a special character.', 'danger')
            return render_template('register.html')

        conn = get_db_connection()
        cursor = conn.cursor()
        if cursor.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        if any(check_password_hash(p[0], password) for p in cursor.execute("SELECT password FROM users").fetchall()):
            flash('This password is already in use by another user.', 'danger')
            return render_template('register.html')

        cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
                       (email, generate_password_hash(password), 'customer'))
        conn.commit()
        conn.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email=? AND role='customer'", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['name'] = user['name'] or "Customer"
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM users WHERE email=? AND role='admin'", (username,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin['password'], password):
            session['admin_id'] = admin['user_id']
            session['admin_name'] = admin['name']
            flash('Admin login successful.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'danger')

    return render_template('admin_login.html')

@app.route('/admin-register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        if len(password) < 6 or not re.search(r'[A-Z]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Password must be at least 6 characters, include an uppercase letter and a special character.', 'danger')
            return render_template('admin_register.html')

        conn = get_db_connection()
        if conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone():
            flash('Email already registered.', 'danger')
            return render_template('admin_register.html')

        conn.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
                     (email, generate_password_hash(password), 'admin'))
        conn.commit()
        conn.close()
        flash('Admin registered! You may now log in.', 'success')
        return redirect(url_for('admin_login'))

    return render_template('admin_register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# -------------------- User & Admin Pages --------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all products with category and restaurant names (your existing code)
    cursor.execute('''
        SELECT menu_items.*, categories.name AS category_name, restaurants.name AS restaurant_name
        FROM menu_items
        JOIN categories ON menu_items.category_id = categories.category_id
        JOIN restaurants ON menu_items.restaurant_id = restaurants.restaurant_id
    ''')
    products = cursor.fetchall()

    # Get all categories
    cursor.execute('SELECT * FROM categories')
    categories = cursor.fetchall()

    # Get cart items for the logged-in user with product details
    cursor.execute('''
        SELECT c.cart_id, c.quantity, m.item_id, m.name, m.price, m.image
        FROM cart c
        JOIN menu_items m ON c.item_id = m.item_id
        WHERE c.user_id = ?
    ''', (session['user_id'],))
    cart_items = cursor.fetchall()

    # Calculate total price of the cart
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)

    conn.close()
    return render_template('dashboard.html', name=session.get('name'), products=products, categories=categories,
                           cart_items=cart_items, total_price=total_price)

    # Get all products with category and restaurant names
    cursor.execute('''
        SELECT menu_items.*, categories.name AS category_name, restaurants.name AS restaurant_name
        FROM menu_items
        JOIN categories ON menu_items.category_id = categories.category_id
        JOIN restaurants ON menu_items.restaurant_id = restaurants.restaurant_id
    ''')
    products = cursor.fetchall()

    # Get all categories
    cursor.execute('SELECT * FROM categories')
    categories = cursor.fetchall()

    conn.close()
    return render_template('dashboard.html', name=session.get('name'), products=products, categories=categories)



@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session['user_id']

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        contact = request.form['contact']
        address = request.form.get('address', '')
        password = request.form['password']
        profile_image = None

        if 'profile_image' in request.files:
            image = request.files['profile_image']
            if image.filename:
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_image = filename

        fields = "name=?, email=?, contact=?, address=?"
        values = [name, email, contact, address]

        if password:
            fields += ", password=?"
            values.append(generate_password_hash(password))

        if profile_image:
            fields += ", profile_image=?"
            values.append(profile_image)

        values.append(user_id)
        cursor.execute(f"UPDATE users SET {fields} WHERE user_id=?", tuple(values))
        conn.commit()

    # Get user info
    user = cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

    # Get orders with item list
    orders_raw = cursor.execute("""
        SELECT o.order_id, o.order_date, o.order_status, o.total_amount
        FROM orders o
        WHERE o.user_id = ?
        ORDER BY o.order_date DESC
    """, (user_id,)).fetchall()

    orders = []
    for o in orders_raw:
        items = cursor.execute("""
            SELECT m.name
            FROM order_details od
            JOIN menu_items m ON od.item_id = m.item_id
            WHERE od.order_id = ?
        """, (o['order_id'],)).fetchall()
        item_list = ', '.join([item['name'] for item in items])
        orders.append({
    'id': o['order_id'],
    'date': o['order_date'],  # use your actual column name here
    'status': o['order_status'],
    'total': o['total_amount'],
    'item_list': item_list  # make sure you consistently use this key
})

    conn.close()
    return render_template('profile.html', user=user, orders=orders)


# -------------------- Admin Panel --------------------
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash('Please log in as admin.', 'warning')
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/admin/overview')
def admin_overview():
    conn = get_db_connection()
    total_orders = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    total_products = conn.execute('SELECT COUNT(*) FROM menu_items').fetchone()[0]
    total_sales = conn.execute('SELECT SUM(total_amount) FROM orders').fetchone()[0] or 0
    total_customers = conn.execute('SELECT COUNT(*) FROM users WHERE role = "customer"').fetchone()[0]
    conn.close()

    return render_template('admin_overview.html',
                           total_orders=total_orders,
                           total_products=total_products,
                           total_sales=total_sales,
                           total_customers=total_customers)

@app.route('/admin/manage')
def admin_manage():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM menu_items').fetchall()
    orders = conn.execute('SELECT * FROM orders').fetchall()
    conn.close()
    return render_template('admin_manage.html', products=products, orders=orders)

@app.route('/admin/add_product', methods=['GET', 'POST'])
def admin_add_product():
    if 'admin_id' not in session:
        flash('Please log in as admin.', 'warning')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category_id = request.form['category_id']
        restaurant_id = request.form['restaurant_id']
        image = request.files['image']
        image_filename = None

        if image and image.filename:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        cursor.execute('''
            INSERT INTO menu_items (name, description, price, category_id, restaurant_id, image)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, price, category_id, restaurant_id, image_filename))

        conn.commit()
        conn.close()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_manage'))

    categories = cursor.execute("SELECT * FROM categories").fetchall()
    restaurants = cursor.execute("SELECT * FROM restaurants").fetchall()
    conn.close()
    return render_template('add_product.html', categories=categories, restaurants=restaurants)

@app.route('/admin/add_category', methods=['GET', 'POST'])
def admin_add_category():
    if 'admin_id' not in session:
        flash('Please log in as admin.', 'warning')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        category_name = request.form['name'].strip()
        if not category_name:
            flash('Category name is required.', 'danger')
            return render_template('add_category.html')

        conn = get_db_connection()
        if conn.execute("SELECT * FROM categories WHERE name = ?", (category_name,)).fetchone():
            flash('Category already exists.', 'danger')
            conn.close()
            return render_template('add_category.html')

        conn.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
        conn.commit()
        conn.close()
        flash('Category added successfully!', 'success')
        return redirect(url_for('admin_manage'))

    return render_template('add_category.html')

@app.route('/admin/add_restaurant', methods=['GET', 'POST'])
def admin_add_restaurant():
    if 'admin_id' not in session:
        flash('Please log in as admin.', 'warning')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name, location, contact = request.form['name'], request.form['location'], request.form['contact']
        conn = get_db_connection()
        conn.execute("INSERT INTO restaurants (name, location, contact) VALUES (?, ?, ?)", (name, location, contact))
        conn.commit()
        conn.close()
        flash('Restaurant added successfully!', 'success')
        return redirect(url_for('admin_manage'))

    return render_template('add_restaurant.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        category_id = request.form['category_id']
        restaurant_id = request.form['restaurant_id']

        cursor.execute('''
            UPDATE menu_items
            SET name = ?, description = ?, price = ?, category_id = ?, restaurant_id = ?
            WHERE item_id = ?
        ''', (name, description, price, category_id, restaurant_id, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_manage'))

    product = cursor.execute('SELECT * FROM menu_items WHERE item_id = ?', (product_id,)).fetchone()
    categories = cursor.execute('SELECT * FROM categories').fetchall()
    restaurants = cursor.execute('SELECT * FROM restaurants').fetchall()
    conn.close()
    return render_template('edit_product.html', product=product, categories=categories, restaurants=restaurants)

@app.route('/admin/delete_product/<int:product_id>')
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM menu_items WHERE item_id = ?', (product_id,))
    conn.commit()
    conn.close()
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('admin_manage'))

# -------------------- Public Product View --------------------
@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def view_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get product info
    cursor.execute('''
        SELECT menu_items.*, categories.name AS category_name, restaurants.name AS restaurant_name
        FROM menu_items
        JOIN categories ON menu_items.category_id = categories.category_id
        JOIN restaurants ON menu_items.restaurant_id = restaurants.restaurant_id
        WHERE item_id = ?
    ''', (product_id,))
    product = cursor.fetchone()

    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('dashboard'))

    # Get product reviews
    cursor.execute('SELECT * FROM reviews WHERE item_id = ?', (product_id,))
    reviews = cursor.fetchall()

    conn.close()
    return render_template('product_detail.html', product=product, reviews=reviews)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        flash("Please log in to add items to your cart.", "warning")
        return redirect(url_for('login'))

    item_id = request.form.get('item_id')
    quantity = request.form.get('quantity', type=int)

    if not item_id or quantity is None or quantity < 1:
        flash("Invalid item or quantity.", "danger")
        return redirect(request.referrer or url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if item already in cart
    cursor.execute('''
        SELECT * FROM cart
        WHERE user_id = ? AND item_id = ?
    ''', (session['user_id'], item_id))
    item = cursor.fetchone()

    if item:
        cursor.execute('''
            UPDATE cart SET quantity = quantity + ?
            WHERE user_id = ? AND item_id = ?
        ''', (quantity, session['user_id'], item_id))
    else:
        cursor.execute('''
            INSERT INTO cart (user_id, item_id, quantity)
            VALUES (?, ?, ?)
        ''', (session['user_id'], item_id, quantity))

    conn.commit()
    conn.close()

    flash("Item added to cart!", "success")
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/leave_review', methods=['POST'])
def leave_review():
    if 'user_id' not in session:
        flash("Please log in to leave a review.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    item_id = int(request.form['item_id'])
    rating = int(request.form['rating'])
    comment = request.form['comment']
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    cursor = conn.cursor()

    existing = cursor.execute('SELECT * FROM reviews WHERE user_id = ? AND item_id = ?', (user_id, item_id)).fetchone()

    if existing:
        # Update existing review
        cursor.execute('''
            UPDATE reviews SET rating = ?, comment = ?, date = ?
            WHERE user_id = ? AND item_id = ?
        ''', (rating, comment, date, user_id, item_id))
        flash('Your review has been updated.', 'info')
    else:
        # Insert new review
        cursor.execute('''
            INSERT INTO reviews (user_id, item_id, rating, comment, date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, item_id, rating, comment, date))
        flash('Your review has been submitted.', 'success')

    conn.commit()
    conn.close()
    return redirect(url_for('view_product', product_id=item_id))

@app.route('/cart/update_quantity/<int:cart_id>/<action>')
def update_cart_quantity(cart_id, action):
    if 'user_id' not in session:
        flash("Please log in.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get current quantity
    cart_item = cursor.execute('SELECT quantity FROM cart WHERE cart_id = ? AND user_id = ?', (cart_id, session['user_id'])).fetchone()
    if not cart_item:
        flash("Cart item not found.", "danger")
        conn.close()
        return redirect(url_for('dashboard'))

    quantity = cart_item['quantity']
    if action == 'add':
        quantity += 1
    elif action == 'reduce' and quantity > 1:
        quantity -= 1

    cursor.execute('UPDATE cart SET quantity = ? WHERE cart_id = ?', (quantity, cart_id))
    conn.commit()
    conn.close()

    return redirect(url_for('orders')) 

@app.route('/cart/remove/<int:cart_id>')
def remove_cart_item(cart_id):
    if 'user_id' not in session:
        flash("Please log in.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart WHERE cart_id = ? AND user_id = ?', (cart_id, session['user_id']))
    conn.commit()
    conn.close()

    flash("Item removed from cart.", "success")
    return redirect(url_for('orders'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash("Please log in to checkout.", "warning")
        return redirect(url_for('login'))

    # For now, just clear cart and thank user
    conn = get_db_connection()
    conn.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
    conn.commit()
    conn.close()

    flash("Checkout successful! Thank you for your order.", "success")
    return redirect(url_for('dashboard'))

@app.route("/cart")
def cart():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT cart.cart_id, menu_items.name, menu_items.price, cart.quantity, menu_items.image
        FROM cart
        JOIN menu_items ON cart.item_id = menu_items.item_id
        WHERE cart.user_id = ?
    ''', (session["user_id"],))
    cart_items = cursor.fetchall()
    conn.close()

    total_price = sum(item["price"] * item["quantity"] for item in cart_items)

    return render_template("cart.html", cart_items=cart_items, total_price=total_price)
    
@app.route('/orders')
def orders():
    return redirect(url_for('cart'))

@app.route('/process_checkout')
def process_checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Get user info
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (session['user_id'],)).fetchone()

    # Get cart items
    cart_items = conn.execute('''
        SELECT c.quantity, m.price
        FROM cart c JOIN menu_items m ON c.item_id = m.item_id
        WHERE c.user_id = ?
    ''', (session['user_id'],)).fetchall()

    product_total = sum(item['quantity'] * item['price'] for item in cart_items)
    shipping_cost = 50  # Fixed shipping for now

    conn.close()

    return render_template('process_checkout.html', user=user,
                           driver_name="Juan Dela Cruz",
                           product_total=product_total,
                           shipping_cost=shipping_cost)

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get cart and user info
    user_id = session['user_id']
    cart_items = conn.execute('''
        SELECT c.item_id, c.quantity, m.price
        FROM cart c JOIN menu_items m ON c.item_id = m.item_id
        WHERE c.user_id = ?
    ''', (user_id,)).fetchall()

    product_total = sum(item['quantity'] * item['price'] for item in cart_items)
    shipping_cost = 50
    total = product_total + shipping_cost
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 1. Create order
    cursor.execute('''
        INSERT INTO orders (user_id, total_amount, order_status, order_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, total, 'Pending', now))
    order_id = cursor.lastrowid

    # 2. Insert order details
    for item in cart_items:
        subtotal = item['quantity'] * item['price']
        cursor.execute('''
            INSERT INTO order_details (order_id, item_id, quantity, subtotal)
            VALUES (?, ?, ?, ?)
        ''', (order_id, item['item_id'], item['quantity'], subtotal))

    # 3. Insert delivery
    cursor.execute('''
        INSERT INTO delivery (order_id, driver_name, delivery_status, estimated_time)
        VALUES (?, ?, ?, ?)
    ''', (order_id, 'Juan Dela Cruz', 'Pending', '2025-05-21 18:00'))
    delivery_id = cursor.lastrowid

    # 4. Insert payment
    cursor.execute('''
        INSERT INTO payments (order_id, amount, payment_method, payment_status, date)
        VALUES (?, ?, ?, ?, ?)
    ''', (order_id, total, 'COD', 'Pending', now))
    payment_id = cursor.lastrowid

    # 5. Update order with delivery and payment ID
    cursor.execute('''
        UPDATE orders SET payment_id = ?, delivery_id = ? WHERE order_id = ?
    ''', (payment_id, delivery_id, order_id))

    # 6. Clear cart
    cursor.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

    flash('Order complete!')
    return redirect(url_for('dashboard'))

@app.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'admin_id' not in session:
        flash('Please log in as admin.', 'warning')
        return redirect(url_for('admin_login'))

    new_status = request.form.get('order_status')
    if not new_status:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin_manage'))

    conn = get_db_connection()
    conn.execute('UPDATE orders SET order_status = ? WHERE order_id = ?', (new_status, order_id))
    conn.commit()
    conn.close()
    flash('Order status updated successfully.', 'success')
    return redirect(url_for('admin_manage'))

@app.route('/admin/products')
def admin_products():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    products = conn.execute('''
        SELECT m.*, c.name AS category_name, r.name AS restaurant_name
        FROM menu_items m
        JOIN categories c ON m.category_id = c.category_id
        JOIN restaurants r ON m.restaurant_id = r.restaurant_id
    ''').fetchall()
    conn.close()

    return render_template('admin_products.html', products=products)

# -------------------- Init DB Route --------------------
@app.route('/initdb')
def create_tables():
    init_db()
    return 'All tables created successfully!'

# -------------------- Run Server --------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
