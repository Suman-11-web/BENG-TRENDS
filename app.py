import sqlite3
import os
from functools import wraps
from flask import Flask, render_template, request, jsonify, g, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_chocolate_key' 
DATABASE = 'chocolate_store.db'
UPLOAD_FOLDER = 'static/products'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password123'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        
        db.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, tagline TEXT, description TEXT,
            price REAL NOT NULL, image_url TEXT NOT NULL, image_url_2 TEXT, image_url_3 TEXT, badge TEXT)''')
            
        db.execute('''CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1), email TEXT, phone TEXT, address TEXT,
            instagram TEXT, facebook TEXT, twitter TEXT, pinterest TEXT, upi_id TEXT, qr_code TEXT)''')
            
        db.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT NOT NULL, phone TEXT NOT NULL,
            address TEXT NOT NULL, total_amount REAL NOT NULL, utr_number TEXT NOT NULL,
            payment_proof TEXT, status TEXT DEFAULT 'Pending Verification', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            landmark TEXT, pincode TEXT, alternate_phone TEXT)''')
        
        # Safely add new columns to existing database
        migrations = [
            "ALTER TABLE orders ADD COLUMN payment_proof TEXT",
            "ALTER TABLE settings ADD COLUMN upi_id TEXT",
            "ALTER TABLE settings ADD COLUMN qr_code TEXT",
            "ALTER TABLE orders ADD COLUMN landmark TEXT",
            "ALTER TABLE orders ADD COLUMN pincode TEXT",
            "ALTER TABLE orders ADD COLUMN alternate_phone TEXT"
        ]
        for migration in migrations:
            try: db.execute(migration)
            except sqlite3.OperationalError: pass
        
        # Initialize default settings if empty
        if db.execute('SELECT COUNT(*) FROM settings').fetchone()[0] == 0:
            db.execute('''INSERT INTO settings (id, email, phone, address, instagram, facebook, twitter, pinterest, upi_id, qr_code)
                VALUES (1, 'hello@bangaloretreats.com', '+91 98765 43210', '123 Joy Lane, Bengaluru', '#', '#', '#', '#', 'yourname@upi', '/static/qr.png')''')
        
        # Ensure existing settings have default payment info if newly upgraded
        db.execute("UPDATE settings SET upi_id = 'yourname@upi' WHERE upi_id IS NULL AND id = 1")
        db.execute("UPDATE settings SET qr_code = '/static/qr.png' WHERE qr_code IS NULL AND id = 1")
        
        db.commit()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- PUBLIC ROUTES ---

@app.route('/')
def index():
    db = get_db()
    settings = db.execute('SELECT * FROM settings WHERE id = 1').fetchone()
    products = db.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    return render_template('index.html', settings=settings, products=products)

@app.route('/shop')
def shop():
    db = get_db()
    settings = db.execute('SELECT * FROM settings WHERE id = 1').fetchone()
    products = db.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    return render_template('shop.html', settings=settings, products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    settings = db.execute('SELECT * FROM settings WHERE id = 1').fetchone()
    if not product: return "Product not found", 404
    return render_template('product.html', product=product, settings=settings)

@app.route('/checkout_page')
def checkout_page():
    settings = get_db().execute('SELECT * FROM settings WHERE id = 1').fetchone()
    return render_template('checkout.html', settings=settings)

@app.route('/checkout_submit', methods=['POST'])
def checkout_submit():
    proof_file = request.files.get('payment_proof')
    proof_path = ""
    if proof_file and proof_file.filename:
        fname = secure_filename(proof_file.filename)
        proof_file.save(os.path.join('static/uploads', fname))
        proof_path = f"/static/uploads/{fname}"

    db = get_db()
    db.execute('''INSERT INTO orders (customer_name, phone, alternate_phone, address, landmark, pincode, total_amount, utr_number, payment_proof) 
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
               (request.form.get('name'), request.form.get('phone'), request.form.get('alternate_phone'), 
                request.form.get('address'), request.form.get('landmark'), request.form.get('pincode'), 
                0.0, request.form.get('utr'), proof_path))
    db.commit()
    return redirect(url_for('success'))

@app.route('/success')
def success():
    settings = get_db().execute('SELECT * FROM settings WHERE id = 1').fetchone()
    return render_template('success.html', settings=settings)

# --- ADMIN ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Invalid credentials! Please try again.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    db = get_db()
    settings = db.execute('SELECT * FROM settings WHERE id = 1').fetchone()
    products = db.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    return render_template('admin.html', settings=settings, products=products, orders=orders)

@app.route('/admin/add_product', methods=['POST'])
@login_required
def add_product():
    img1 = request.files.get('image1')
    if not img1 or not img1.filename:
        flash("Primary Image is required!")
        return redirect(url_for('admin_dashboard'))
    
    paths = []
    for img in [img1, request.files.get('image2'), request.files.get('image3')]:
        if img and img.filename:
            fname = secure_filename(img.filename)
            img.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            paths.append(f"/{app.config['UPLOAD_FOLDER']}/{fname}")
        else:
            paths.append(None)

    db = get_db()
    db.execute('INSERT INTO products (name, tagline, description, price, badge, image_url, image_url_2, image_url_3) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
               (request.form['name'], request.form['tagline'], request.form['description'], request.form['price'], request.form['badge'], paths[0], paths[1], paths[2]))
    db.commit()
    flash("Product added successfully!")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/sync_products', methods=['POST'])
@login_required
def sync_products():
    db = get_db()
    existing_products = db.execute('SELECT image_url FROM products').fetchall()
    existing_urls = [row['image_url'] for row in existing_products]
    product_folder = app.config['UPLOAD_FOLDER']
    added_count = 0
    
    for filename in os.listdir(product_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
            img_path = f"/{product_folder}/{filename}"
            if img_path not in existing_urls:
                clean_name = os.path.splitext(filename)[0].replace('_', ' ').title()
                db.execute('''INSERT INTO products (name, tagline, description, price, badge, image_url) 
                              VALUES (?, ?, ?, ?, ?, ?)''', 
                           (clean_name, 'Delicious Bangalore Treat', 'Click Edit in the admin dashboard to update this description.', 199.0, '', img_path))
                added_count += 1
                
    db.commit()
    flash(f"Successfully synced {added_count} new images as products!")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_product/<int:product_id>', methods=['POST'])
@login_required
def edit_product(product_id):
    db = get_db()
    db.execute('UPDATE products SET name=?, tagline=?, description=?, price=?, badge=? WHERE id=?',
               (request.form['name'], request.form['tagline'], request.form['description'], request.form['price'], request.form['badge'], product_id))
    
    for idx, key in enumerate(['image1', 'image2', 'image3']):
        img = request.files.get(key)
        if img and img.filename:
            fname = secure_filename(img.filename)
            img.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            col = 'image_url' if idx == 0 else f'image_url_{idx+1}'
            db.execute(f'UPDATE products SET {col}=? WHERE id=?', (f"/{app.config['UPLOAD_FOLDER']}/{fname}", product_id))
            
    db.commit()
    flash(f"Product updated successfully!")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    db = get_db()
    db.execute('DELETE FROM products WHERE id = ?', (product_id,))
    db.commit()
    flash(f"Product deleted successfully.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_settings', methods=['POST'])
@login_required
def update_settings():
    db = get_db()
    
    # Handle optional QR Code Upload
    qr_file = request.files.get('qr_code')
    if qr_file and qr_file.filename:
        fname = secure_filename(qr_file.filename)
        qr_file.save(os.path.join('static/uploads', fname))
        db.execute('UPDATE settings SET qr_code=? WHERE id=1', (f"/static/uploads/{fname}",))
        
    db.execute('''UPDATE settings SET email=?, phone=?, address=?, instagram=?, facebook=?, twitter=?, pinterest=?, upi_id=? WHERE id=1''',
               (request.form['email'], request.form['phone'], request.form['address'], request.form['instagram'], request.form['facebook'], request.form['twitter'], request.form['pinterest'], request.form['upi_id']))
    db.commit()
    flash("Settings updated successfully!")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    db = get_db()
    db.execute('UPDATE orders SET status = ? WHERE id = ?', (request.form.get('status'), order_id))
    db.commit()
    flash(f"Order status updated to {request.form.get('status')}.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_order/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    db = get_db()
    db.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    db.commit()
    flash(f"Order permanently deleted.")
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=8080, debug=True)