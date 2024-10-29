from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openpyxl import Workbook
from io import BytesIO

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit image size to 16 MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.secret_key = 'hamasisisis'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/download-data', methods=['GET'])
def download_data():

    leads = query("SELECT * FROM leads")
    product_orders = query("SELECT * FROM products_order")
    products = query("SELECT * FROM products")
    costumers = query("SELECT * FROM costumer_club")

    # Create a new Excel workbook
    wb = Workbook()

    # Add a sheet for each section
    # Leads sheet
    leads_ws = wb.active
    leads_ws.title = "Leads"
    leads_ws.append(["ID", "שם", "טלפון", "תאריך", "סטטוס"])
    for lead in leads:  # Assuming `leads` is fetched from the database
        leads_ws.append(lead)

    # Customer Club sheet
    customer_ws = wb.create_sheet(title="Customer Club")
    customer_ws.append(["ID", "שם", "טלפון", "אימייל", "תאריך", "אישור התראות"])
    for customer in costumers:  # Assuming `customers` is fetched from the database
        customer_ws.append(customer)

    # Product Orders sheet
    orders_ws = wb.create_sheet(title="Product Orders")
    orders_ws.append(["ID", "תאריך", "שם", "טלפון", "הזמנות", "סטטוס"])
    for order in product_orders:  # Assuming `product_orders` is fetched from the database
        orders_ws.append(order)

    # Stock sheet
    stock_ws = wb.create_sheet(title="Stock")
    stock_ws.append(["ID","שם המוצר","קטגוריה","מחיר","תיאור","תמונה","כמות במלאי", "משקל מוצר", "האם מוגדר פופולארי","סוג חיה"])
    for product in products:  # Assuming `products` is fetched from the database
        stock_ws.append(product)

    # Save the workbook to a BytesIO object
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # Send the file as a download
    return send_file(output, as_attachment=True, download_name="admin_data.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route('/')
def home():
    if 'products_in_cart' not in session:
        session['products_in_cart'] = {}
    adopt = query(f"SELECT * FROM adopt ORDER BY id DESC LIMIT 1")
    products = query(f"SELECT * FROM products")
    products_on_sale = [product for product in products if product[10] == "כן"]
    first_product_on_sale = products_on_sale[0] if products_on_sale else None
    popular_products = []
    for product in products:
        if product[8] == "כן":
            popular_products.append(product)    
    return render_template('home.html', popular_products=popular_products, adopt=adopt,first_product_on_sale=first_product_on_sale )

@app.route('/about')
def about():  
    return render_template('about.html')


@app.route('/catalog', methods=['GET','POST'])
def catalog():
    animal_type = request.args.get('animal')  # Get the animal type from query parameters
    category = request.args.get('category')  # Get the animal type from query parameters
    if animal_type:
        products = query(f"SELECT * FROM products WHERE animal = '{animal_type}'")
        if category:
            products = query(f"SELECT * FROM products WHERE category = '{category}' and animal = '{animal_type}'")
    elif category:
        products = query(f"SELECT * FROM products WHERE category = '{category}'")
    else:
        products = query(f"SELECT * FROM products")
    return render_template('catalog.html', products=products)

# @app.route('/api/products', methods=['GET'])
# def api_products():
#     products_json = []
#     products = query(f"SELECT * FROM products")
#     for product in products:
#         product_json = {
#             "id": product[0], 
#             "product_name": product[1], 
#             "category": product[2], 
#             "price": product[3], 
#             "description": product[4],
#             "image": product[0],  
#             "stock": product[6], 
#             "weight": product[7],
#             "popular": product[8],
#             "animal": product[9]
#         }
#         products_json.append(product_json)

#     return json.dumps(products_json, ensure_ascii=False)


@app.route('/show_product', methods=['POST', 'GET'])
def show_product():
    product_id = request.form.get('product_id')
    product = query(sql=f"SELECT * FROM products WHERE id={product_id}")

    if product:
        return render_template('show_product.html', product=product[0])  # Pass the first item in the list
    else:
        return render_template('show_product.html', error="Product not found")


@app.route('/search', methods=['GET', 'POST'])
def search():
    text = request.args.get('text')  # Use 'GET' since it's a form with GET method
    if text:
        sql = f"SELECT * FROM products WHERE category LIKE '%{text}%' OR product_name LIKE '%{text}%' OR animal LIKE '%{text}%' OR description LIKE '%{text}%'"
        products = query(sql)
        return render_template('catalog.html', products=products)
    else:
        return redirect('/catalog')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "new"  # Default status

        # Insert into leads table using raw SQL
        insert_sql = f"INSERT INTO leads (name, phone, date, status) VALUES ('{name}', '{phone}', '{date}', '{status}')"
        query(insert_sql)  # Call existing query function for execution
        send_contact_email(name, phone, date)
        flash("תודה שיצרת קשר! נחזור אלייך בהקדם האפשרי", 'contact')  # Add category here
    return redirect('/')  # Redirect to the cart page
@app.route('/cart', methods=['GET', 'POST'])
def cart():
    products_in_cart = session.get('products_in_cart', {})  # This is a dictionary {product_id: quantity}
    product_details_in_cart = []  # Create a new list to hold product details
    total_price = 0  # Initialize total price

    for product_id, quantity in products_in_cart.items():  # Loop through the dictionary
        product = query(f"SELECT * FROM products WHERE id={product_id}")
        if product:
            product_info = product[0]
            product_info = list(product_info)  # Convert product tuple to list so we can modify it
            product_info.append(quantity)  # Add the quantity as part of product info

            # Check if there is a discount (assuming the discount is in column 12, i.e., product[12])
            discount = product_info[12] if len(product_info) > 12 else 0
            price = product_info[3]  # Original price

            if discount > 0:
                # Calculate the discounted price
                discounted_price = price - (price * discount / 100)
            else:
                # No discount, use the original price
                discounted_price = price

            # Add the discounted price and quantity to the product info
            product_info.append(quantity * discounted_price)  # Calculate total price for this product
            product_details_in_cart.append(product_info)  # Collect product info with quantity and discount

            # Accumulate total price including discount
            total_price += quantity * discounted_price

    return render_template('cart.html', products=product_details_in_cart, total_price=total_price)

@app.route('/remove_cart', methods=['POST'])
def remove_cart():
    products_in_cart = session.get('products_in_cart', {})  # Retrieve the dictionary from the session
    product_to_remove = request.form.get('remove')  # Get the product ID to remove
    
    if product_to_remove in products_in_cart:
        del products_in_cart[product_to_remove]  # Remove the product from the dictionary

    session['products_in_cart'] = products_in_cart  # Update the session with the modified cart
    return redirect('/cart')

@app.route('/update_cart', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id')
    new_quantity = int(request.form.get('quantity'))
    products_in_cart = session.get('products_in_cart', {})
    if product_id in products_in_cart:
        products_in_cart[product_id] = new_quantity  # Update quantity for the product
    
    session['products_in_cart'] = products_in_cart
    return redirect('/cart')

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id') 
    products_in_cart = session.get('products_in_cart', {})  
    if product_id in products_in_cart:
        products_in_cart[product_id] += 1
    else:
        products_in_cart[product_id] = 1
        
    session['products_in_cart'] = products_in_cart
    return redirect('/cart')



@app.route('/submit_order', methods=['POST'])
def submit_order():
    try:
        name = request.form.get('name')
        phone = request.form.get('phone')
        products_in_cart = session.get('products_in_cart', {})  # Make sure to get the cart as a dictionary
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "new"

        products_in_cart_str = ', '.join(f"{product_id}:{quantity}" for product_id, quantity in products_in_cart.items())

        query(f"INSERT INTO products_order (date, name, phone, products_order, status) VALUES ('{date}', '{name}', '{phone}', '{products_in_cart_str}', '{status}')"),

        send_order_email(name, phone, products_in_cart_str, date)

        session.pop('products_in_cart', None)  # Clear cart after submission
        flash("קיבלנו את ההזמנה!  נחזור אלייך בהקדם האפשרי")
        return redirect('/cart')  # Redirect to the cart page

    except Exception as e:
        # Log the error and flash a message
        print(f"Error occurred: {e}")  # You can log this to a file or logging service
        flash("אירעה שגיאה בהגשת ההזמנה. אנא נסה שוב.")
        return redirect('/cart')  # Redirect to the cart page in case of error

    if __name__ == '__main__':
        app.run(debug=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = "ari"
        password = "ari123"
        user_username = request.form.get('username') 
        user_password = request.form.get('password')  # Corrected key

        if username == user_username and password == user_password:
            return admin()
    
    return render_template('login.html')

@app.route('/admin')
def admin():
    leads = query("SELECT * FROM leads")
    product_orders = query("SELECT * FROM products_order")
    products = query("SELECT * FROM products")
    costumers = query("SELECT * FROM costumer_club")
    return render_template('admin.html', leads=leads, product_orders=product_orders, products=products, costumers=costumers)

@app.route('/update_lead_status', methods=['POST'])
def update_lead_status():
    lead_id = request.form.get('lead_id')  # Get the lead ID from the form
    status = request.form.get('status')    # Get the new status from the dropdown

    # Update the lead's status in the database
    query(f"UPDATE leads SET status = '{status}' WHERE id = '{lead_id}'")

    # Redirect back to the admin page
    return redirect('/admin')

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    order_id = request.form.get('order_id')  # Get the order ID from the form
    status = request.form.get('status')      # Get the new status from the dropdown

    # Update the order's status in the database
    query(f"UPDATE products_order SET status = ? WHERE id = ?", (status, order_id))

    # Redirect back to the admin page
    return redirect('/admin')

@app.route('/update_stock', methods=['POST'])
def update_stock():
    # Get the form data
    product_id = request.form.get('product_id')
    name = request.form.get('name')
    category = request.form.get('category')
    price = float(request.form.get('price'))  # Ensure price is a float
    description = request.form.get('description')
    popular = request.form.get('popular')
    animal = request.form.get('animal')
    stock = int(request.form.get('stock'))  # Ensure stock is an integer
    weight = request.form.get('weight')
    monthly_sale = request.form.get('monthly_sale')
    sale = request.form.get('sale')
    discount =request.form.get('discount')


    # Update the product's details in the database
    query(f"""
        UPDATE products 
    SET product_name = ?, category = ?, price = ?, description = ?, popular = ?, animal = ?, stock = ?, weight = ?, 
    monthly_sale = ?, sale = ?, discount = ? 
    WHERE id = ?
    """, (name, category, price, description, popular, animal, stock, weight, monthly_sale, sale, discount, product_id))

    # Redirect back to the admin page
    return redirect('/admin')

@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    description = request.form['description']
    category = request.form['category']
    popular = request.form['popular']
    price = float(request.form['price'])  # Ensure price is a float
    stock = int(request.form['stock'])  # Ensure stock is an integer
    animal = request.form['animal']
    weight = request.form.get('weight')
    monthly_sale = 'לא'
    sale = 'לא'
    discount = 0

    image = request.files['image']
    image_filename = 'none'
    if image and allowed_file(image.filename):
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    query(f"INSERT INTO products (product_name, category, price, description, image, stock, weight, popular, animal, monthly_sale, sale, discount)  VALUES ('{name}', '{category}', '{price}', '{description}', '{image_filename}', '{stock}', '{weight}', '{popular}', '{animal}', '{monthly_sale}', '{sale}', '{discount}')")
    return redirect('/admin')

@app.route('/add_adopt', methods=['POST'])
def add_adopt():
    name = request.form['name']
    description = request.form['description']
    type = request.form['type']
    age = int(request.form['age'])
    image = request.files['image']
    image_filename = 'none'
    if image and allowed_file(image.filename):
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
    
    query(f"INSERT INTO adopt (name, type, age, description, image) VALUES ('{name}', '{type}', '{age}', '{description}', '{image_filename}')")   
    return redirect('/admin')

@app.route('/customer-club-signup', methods=['POST'])
def customer_club_signup():
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    confirmation = request.form.get('agree_updates')
    query(f"INSERT INTO costumer-club (name, phone, email, date, confirmation) VALUES ('{name}', '{phone}', '{email}', '{date}', '{confirmation}')")   
    send_costumer_club_email(name, phone, email, date, confirmation)
    flash("תודה שהצטרפתם למועדון הלקוחות שלנו!", "promo")
    return redirect('/')

#db

def query(sql: str = "", params: tuple = (), db_name="petforme.db"):
    try:
        with sqlite3.connect(db_name) as conn:
            cur = conn.cursor()
            cur.execute(sql, params)  # Pass parameters to execute
            if sql.strip().lower().startswith('select'):
                return cur.fetchall()  # Fetch all results for SELECT queries
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    
def create_table_products(table="products"):
    sql = f"CREATE TABLE IF NOT EXISTS {table} (class_id NT AUTO_INCREMENT PRIMARY KEY, product_name TEXT, category TEXT)"
    query(sql)

import os

sender_email = os.environ.get("SENDER_EMAIL")
sender_password = os.environ.get("SENDER_PASSWORD")

def send_order_email(name, phone, products, order_date):
    # Email configuration
    sender_email = "ofirital0@gmail.com"
    sender_password = "asfl tyti jmdi ukfw"
    receiver_email = "ofirital0@gmail.com"

    # Parse the products string into a list of tuples (product_id, quantity)
    product_items = [item.split(':') for item in products.split(', ')]
    
    # Extract product_ids
    product_ids = [item[0] for item in product_items]

    # Create the SQL query to fetch product names
    product_names_query = f"SELECT id, product_name FROM products WHERE id IN ({', '.join('?' for _ in product_ids)})"
    
    # Execute the query with the product_ids
    product_names = query(product_names_query, tuple(product_ids))

    if product_names is None:
        print("Failed to fetch product names from the database.")
        return  # Early return if there was an issue

    # Create a dictionary for easy lookup of product names
    product_dict = {str(product[0]): product[1] for product in product_names}

    # Create the email content using HTML
    order_details = []
    for product_id, quantity in product_items:
        product_name = product_dict.get(product_id, "Unknown Product")
        order_details.append((product_name, quantity))

    # Build the HTML content for the email
    order_details_html = ''.join(
        f"<tr><td>{product_name}</td><td>{quantity}</td></tr>" for product_name, quantity in order_details
    )

    html_body = f"""
    <html>
    <body>
        <h2>הזמנה חדשה נכנסה</h2>
        <p>תאריך: {order_date}</p>
        <p>שם המזמין: {name}</p>
        <p>טלפון: {phone}</p>
        <table style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr>
                    <th style="border: 1px solid #ddd; padding: 8px;">שם המוצר</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">כמות</th>
                </tr>
            </thead>
            <tbody>
                {order_details_html}
            </tbody>
        </table>
    </body>
    </html>
    """

    # Create the email message
    msg = MIMEMultipart('alternative')  # Set the email to send both plain text and HTML
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "New PET4ME Order"

    # Attach both plain text and HTML versions
    msg.attach(MIMEText("This email requires HTML support.", 'plain'))  # Fallback for non-HTML email clients
    msg.attach(MIMEText(html_body, 'html'))  # HTML version

    try:
        # Connect to the SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("Order confirmation email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_costumer_club_email(name, phone, email, date, confirmation):
    # Email configuration
    sender_email = "ofirital0@gmail.com"
    sender_password = "asfl tyti jmdi ukfw"
    receiver_email = "ofirital0@gmail.com"
    
   
    html_body = f"""
    <html>
    <body>
        <h2>הצטרפות למועדון לקוחות</h2>
        <p>תאריך: {date}</p>
        <p>שם מלא: {name}</p>
        <p>טלפון: {phone}</p>
        <p>אימייל: {email}</p>
        <p>אישר קבלת פרטים {confirmation}</p>
    </body>
    </html>
    """

    # Create the email message
    msg = MIMEMultipart('alternative')  # Set the email to send both plain text and HTML
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "New PET4ME Costumer Club"

    # Attach both plain text and HTML versions
    msg.attach(MIMEText("This email requires HTML support.", 'plain'))  # Fallback for non-HTML email clients
    msg.attach(MIMEText(html_body, 'html'))  # HTML version

    try:
        # Connect to the SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("costumer club requset email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")



def send_contact_email(name, phone, date):
    # Email configuration
    sender_email = "ofirital0@gmail.com"
    sender_password = "asfl tyti jmdi ukfw"
    receiver_email = "ofirital0@gmail.com"
    
   
    html_body = f"""
    <html>
    <body>
        <h2>בקשה ליצירת קשר</h2>
        <p>תאריך: {date}</p>
        <p>שם מלא: {name}</p>
        <p>טלפון: {phone}</p>
    </body>
    </html>
    """

    # Create the email message
    msg = MIMEMultipart('alternative')  # Set the email to send both plain text and HTML
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "New PET4ME Contact Request"

    # Attach both plain text and HTML versions
    msg.attach(MIMEText("This email requires HTML support.", 'plain'))  # Fallback for non-HTML email clients
    msg.attach(MIMEText(html_body, 'html'))  # HTML version

    try:
        # Connect to the SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("contact requset email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


