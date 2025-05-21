from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------- Get DB Connection --------------------
def get_db_connection():
    conn = sqlite3.connect('food_ordering.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_all_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category_id, name FROM categories")
    categories = cursor.fetchall()
    conn.close()
    return categories

# -------------------- Initialize DB --------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            restaurant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            location TEXT,
            contact TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    ''')

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_id INTEGER,
            comment TEXT,
            date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # Create default admin if not exists
    cursor.execute("SELECT * FROM users WHERE email = 'admin@example.com'")
    if not cursor.fetchone():
        hashed_admin_pw = generate_password_hash("admin123!")
        cursor.execute('''
            INSERT INTO users (name, email, contact, address, password, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Admin', 'admin@example.com', '0000000000', 'Admin HQ', hashed_admin_pw, 'admin'))
        print("✅ Default admin created: admin@example.com / admin123!")

    conn.commit()
    conn.close()

# -------------------- Routes --------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if len(password) < 6 or not re.search(r'[A-Z]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Password must be at least 6 characters, include an uppercase letter and a special character.', 'danger')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        if cursor.fetchone():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        cursor.execute("SELECT password FROM users")
        existing_passwords = [row[0] for row in cursor.fetchall()]
        for p in existing_passwords:
            if check_password_hash(p, password):
                flash('This password is already in use by another user.', 'danger')
                return render_template('register.html')

        cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (email, hashed_password, 'customer'))
        conn.commit()
        conn.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND role='customer'", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['name'] = user['name'] or "Customer"
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND role='admin'", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and check_password_hash(admin['password'], password):
            session['admin_id'] = admin['user_id']
            session['admin_name'] = admin['name']
            flash('Admin login successful.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')

    return render_template('admin_login.html')

@app.route('/admin-register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if len(password) < 6 or not re.search(r'[A-Z]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            flash('Password must be at least 6 characters, include an uppercase letter and a special character.', 'danger')
            return render_template('admin_register.html')

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        if cursor.fetchone():
            flash('Email already registered.', 'danger')
            return render_template('admin_register.html')

        cursor.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (email, hashed_password, 'admin'))
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session.get('name'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        contact = request.form['contact']
        address = request.form.get('address', '')
        password = request.form['password']
        profile_image = None

        if 'profile_image' in request.files:
            image = request.files['profile_image']
            if image and image.filename != '':
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_image = filename

        update_fields = "name=?, email=?, contact=?, address=?"
        params = [name, email, contact, address]

        if password:
            update_fields += ", password=?"
            params.append(generate_password_hash(password))

        if profile_image:
            update_fields += ", profile_image=?"
            params.append(profile_image)

        params.append(user_id)
        cursor.execute(f"UPDATE users SET {update_fields} WHERE user_id=?", tuple(params))
        conn.commit()
        conn.close()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash('Please log in as admin.', 'warning')
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/admin/overview')
def admin_overview():
    return render_template('admin_overview.html')

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
        restaurant_id = request.form['restaurant_id']  # <-- Now it exists in the form

        image = request.files['image']
        image_filename = None
        if image:
            image_filename = image.filename
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))


        cursor.execute("""
            INSERT INTO menu_items (name, description, price, category_id, restaurant_id, image)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, description, price, category_id, restaurant_id, image_filename))

        conn.commit()
        conn.close()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_manage'))

    # GET request: fetch categories and restaurants
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    cursor.execute("SELECT * FROM restaurants")
    restaurants = cursor.fetchall()
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
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE name = ?", (category_name,))
        if cursor.fetchone():
            flash('Category already exists.', 'danger')
            conn.close()
            return render_template('add_category.html')

        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
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
        name = request.form['name']
        location = request.form['location']
        contact = request.form['contact']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO restaurants (name, location, contact)
            VALUES (?, ?, ?)
        """, (name, location, contact))
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

    cursor.execute('SELECT * FROM menu_items WHERE item_id = ?', (product_id,))
    product = cursor.fetchone()

    cursor.execute('SELECT * FROM categories')
    categories = cursor.fetchall()

    cursor.execute('SELECT * FROM restaurants')
    restaurants = cursor.fetchall()

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

@app.route('/initdb')
def create_tables():
    init_db()
    return 'All tables created successfully!'

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
