import os
from dotenv import load_dotenv
from collections import Counter
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from flask_socketio import SocketIO
from flask_socketio import join_room

# there are admin called: ' with password:  '  
#  yes that was a quote as the name and pass
# and a super admin called: "admin" with password: "admin123"

#load_dotenv()  # reads the .env file in the project folder and loads it into os.environ

app = Flask(__name__)
# Reads SECRET_KEY from .env (via load_dotenv above); falls back to a random
# key each restart if .env is missing (fine for a quick test, but sessions
# won't survive a server restart without a real key in .env).


#we put a secret key here for testing purposes and simplicity.
app.secret_key = 'secret123'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
socketio = SocketIO(app)
db = SQL("sqlite:///database/cafe.db")

@socketio.on('connect')
def handle_connect():
    if session.get("user_id"):
        room = f"user_{session['user_id']}"
        join_room(room)

@app.context_processor
def inject_flash_helpers():
    def flash_class(category):
        mapping = {
            "success": "success",
            "warning": "warning",
            "info": "info",
            "danger": "danger",
            "error": "danger",
        }
        return mapping.get(category or "", "info")

    def format_price(value):
        formatted = f"{float(value):.2f}"
        return formatted.rstrip("0").rstrip(".")

    return {"flash_class": flash_class, "format_price": format_price}

def login_required(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        if session.get("user_id") is None:
            flash('you need to login first!', 'warning')
            return redirect("/login")
        return func(*args, **kwargs)
    return decorator

def admin_required(func):
    @wraps(func)
    def decorator_func(*args, **kwargs):
        if session.get("role") != "admin":
            flash('NOT ALLOWED', 'danger')
            return redirect("/")
        return func(*args, **kwargs)
    return decorator_func
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return render_template("register.html", message="Please provide a username")
        if not request.form.get("password"):
            return render_template("register.html", message="Please provide a password")
        if not request.form.get("confirm_password"):
            return render_template("register.html", message="Please confirm your password")
        if request.form.get("password") != request.form.get("confirm_password"):
            return render_template("register.html", message="Passwords do not match")
        user_name = request.form.get("username")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)
        try:
            db.execute('INSERT INTO users (user_name, password_hash) Values (?, ?)', user_name, hashed_password)
            return redirect("/login")
        except Exception:
            return render_template("register.html", message="Username already exists")
        
    else:
        return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        session.clear()
        user_name = request.form.get('user_name')
        password = request.form.get('password')
        if not user_name:
            return render_template('login.html', error = 'Please enter a username')
        elif not password:
            return render_template('login.html', error = 'Please enter a password')
        user = db.execute('SELECT * FROM users WHERE user_name = ?', (user_name))
        if user and check_password_hash(user[0]['password_hash'], password): 
            session['user_id'] = user[0]['id']
            session['user_name'] = user[0]['user_name']
            session['role'] = user[0]['role']
            session['points'] = user[0]['points']
            session['cart'] = []  # Initialize an empty cart for the user
            session.modified = True  # Mark the session as modified to save changes
            if session['role'] == 'admin':
                return redirect('/dashboard')
           
            return redirect('/menu')
        else:
            return render_template('login.html', error = "incorrect password or username")
    return render_template('login.html')
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    role = session.get("role")
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        if not current_password or not new_password or not confirm_new_password:
            return render_template("change_password.html", error = "all fields are required.")

        if new_password != confirm_new_password:
            return render_template("change_password.html", error= "New passwords do not match.")
        
        user_id = session.get("user_id")
        user = db.execute("SELECT * FROM users WHERE id = ?", user_id)

        if not check_password_hash(user[0]["password_hash"], current_password):
            return render_template("change_password.html", error= "Current password is incorrect.")

        hashed_new_password = generate_password_hash(new_password)
        try:
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?", hashed_new_password, user_id)
            flash("Password changed successfully!", "success")
        except Exception as e:
            flash(f"An error occurred while changing the password: {e}", "danger")
        if role == 'admin':
            return redirect("/dashboard")
        else:
            return redirect("/menu")

    return render_template("change_password.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/")

@app.route("/", methods=["GET", "POST"])
def index():
    # we need to add an if statment for admin here when we get to stage 4 
    if request.method == "GET" and session.get("user_id"):
        if session.get("role") == "admin":
            return redirect("/dashboard")
        else:
            return redirect("/menu")
    return render_template("index.html")
    
@app.route("/menu")
@login_required
def menu():
    items = db.execute("SELECT * FROM menu_items WHERE is_available = TRUE")
    return render_template("menu.html", items=items)

def add_to_cart(item_id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(item_id)
    session.modified = True
    socketio.emit('cart_updated', {'cart_count': len(session['cart'])}, to=f"user_{session['user_id']}")


@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart_route():
    item_id = int(request.form.get('item_id'))
    add_to_cart(item_id)
    return jsonify({'status': 'success'})

def remove_from_cart(item_id):
    if 'cart' in session and item_id in session['cart']:
        session['cart'].remove(item_id)
        session.modified = True
        socketio.emit('cart_updated', {'cart_count': len(session['cart'])}, to=f"user_{session['user_id']}")

@app.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    cart_ids = session.get('cart', []) 
    cart_items = []
    total_price =0

    if request.method == 'POST' and request.form.get('item_id'):
        item_id = int(request.form.get('item_id'))
        remove_from_cart(item_id)
        cart_ids = session.get('cart', [])

    if cart_ids:
        item_counts = Counter(cart_ids)
        unique_cart_ids = list(item_counts.keys())
        db_items = db.execute("SELECT id, name, price FROM menu_items WHERE id IN (?)", unique_cart_ids)
        for item in db_items:
                    item['quantity'] = item_counts[item['id']]
                    item['subtotal'] = item['price'] * item['quantity']
                    cart_items.append(item)
                    total_price += item['subtotal']
    if request.method == 'POST':
        return jsonify({'items': cart_items, 'total_price': total_price})
    return render_template('cart.html', items=cart_items, total=total_price)
@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    user_id = session.get('user_id')
    cart_ids = session.get('cart', [])
    if not cart_ids:
        return redirect('/menu')
    item_counts = Counter(cart_ids)
    unique_cart_ids = list(item_counts.keys())
    db_items = db.execute("SELECT * FROM menu_items WHERE id IN (?) AND is_available = TRUE", unique_cart_ids)

    valid_ids = []
    for item in db_items:
        valid_ids.append(item['id'])
    if not db_items or len(db_items) != len(unique_cart_ids):
        update_cart=[]
        for item_id in cart_ids:
            if item_id in valid_ids:
                update_cart.append(item_id)
        session['cart'] = update_cart
        session.modified = True
        flash("Some items are no longer available", "error") 
        return redirect("/menu")       
            
    subtotal = sum(item['price'] * item_counts[item['id']] for item in db_items)

    point = db.execute("SELECT points FROM users WHERE  id= ?", user_id)
    if point:
        current_points = point[0]['points']
    else: 
        current_points = 0    

    if current_points >= 5:
        total_price = round(subtotal * 0.75, 2)
        db.execute("UPDATE users SET points = 0 WHERE id= ?", user_id)
        session["points"] = 0
        flash(f"Congrats! You got 25% discount. Your new total price is: ${total_price}", "success")
    else:
        total_price = round(subtotal, 2) 
        if total_price >10:
            current_points +=1
            db.execute("UPDATE users SET points = points +1 WHERE id = ?", user_id)    
            session["points"] = session.get("points") + 1


    order_id = db.execute("INSERT INTO orders (user_id, total_price, status) VALUES (?, ?, 'pending')", user_id, total_price)
    for item in db_items:
        quantity = item_counts[item['id']]
        db.execute("INSERT INTO order_items (order_id, menu_item_id, price, quantity) VALUES (?, ?, ?, ?)", 
               order_id, item['id'], item['price'], quantity)
    session['cart'].clear()
    session.modified = True
    socketio.emit('new_order')
    socketio.emit('cart_updated', {'cart_count': len(session['cart'])}, to=f"user_{session['user_id']}")
    flash("Order placed successfully!", "success")
    return redirect('/my_orders')
@app.route("/my_orders")
@login_required
def my_orders():
    user_id = session.get('user_id')
    orders = db.execute("SELECT * FROM orders WHERE user_id = ?", user_id)
    for order in orders:
        order_items = db.execute("SELECT menu_items.name, order_items.price, order_items.quantity FROM order_items JOIN menu_items ON order_items.menu_item_id = menu_items.id WHERE order_items.order_id = ?", order['id'])
        order['items'] = order_items
        total_price = 0
        for item in order_items:
            item['subtotal'] = item['price'] * item['quantity']
            total_price += item['subtotal']
        order['total_price'] = total_price

    return render_template("my_orders.html", orders=sorted(orders, key=lambda x: x['created_at'], reverse=True))
@app.route('/dashboard')
@login_required
@admin_required
def dashboard():
    return render_template("dashboard.html")

@app.route('/api/new_orders')
@login_required
@admin_required
def api_orders():
    pending_orders = db.execute(
        "SELECT orders.id, orders.status, users.user_name "
        "FROM orders "
        "JOIN users ON orders.user_id = users.id "
        "WHERE orders.status = 'pending' "
        "ORDER BY orders.created_at DESC"
    )
    for order in pending_orders:
        order_items = db.execute(
            "SELECT menu_items.name, order_items.price, order_items.quantity "
            "FROM order_items "
            "JOIN menu_items ON order_items.menu_item_id = menu_items.id "
            "WHERE order_items.order_id = ?",
            order['id']
        )
        order['items'] = order_items
    return jsonify({"pending_orders": pending_orders})

@app.route('/kitchen')
@login_required
@admin_required
def kitchen():
    pending_orders = db.execute("SELECT orders.id, orders.status, users.user_name FROM orders JOIN users ON orders.user_id = users.id WHERE orders.status = 'pending' ORDER BY orders.created_at DESC")
    for order in pending_orders:
        order_items = db.execute("SELECT menu_items.name, order_items.price, order_items.quantity FROM order_items JOIN menu_items ON order_items.menu_item_id = menu_items.id WHERE order_items.order_id = ?", order['id'])
        order['items'] = order_items

    preparing_orders = db.execute("SELECT orders.id, orders.status, users.user_name FROM orders JOIN users ON orders.user_id = users.id WHERE orders.status = 'preparing' ORDER BY orders.created_at DESC")
    for order in preparing_orders:
        order_items = db.execute("SELECT menu_items.name, order_items.price, order_items.quantity FROM order_items JOIN menu_items ON order_items.menu_item_id = menu_items.id WHERE order_items.order_id = ?", order['id'])
        order['items'] = order_items
        
    completed_orders = db.execute("SELECT orders.id, orders.status, users.user_name FROM orders JOIN users ON orders.user_id = users.id WHERE orders.status = 'completed' ORDER BY orders.created_at DESC")
    for order in completed_orders:
        order_items = db.execute("SELECT menu_items.name, order_items.price, order_items.quantity FROM order_items JOIN menu_items ON order_items.menu_item_id = menu_items.id WHERE order_items.order_id = ?", order['id'])    
        order['items'] = order_items
    return render_template("kitchen.html", pending_orders=pending_orders, preparing_orders=preparing_orders, completed_orders=completed_orders)

@app.route("/admin/update_status", methods=["POST"])
@login_required
@admin_required
def update_status():
    data = request.get_json()
    order_id = data.get("order_id")
    new_status = data.get("new_status")
    if not order_id or not new_status:
        return jsonify({"success": False, "error": "Missing data"}), 400
    db.execute("UPDATE orders SET status = ? WHERE id = ?", new_status, order_id)
    if new_status == "completed":
        order = db.execute("SELECT user_id FROM orders WHERE id = ?", order_id)
        db.execute("INSERT INTO notifications (user_id, message, type) VALUES (?, ?, ?)", order[0]["user_id"], f"your order number #{order_id} is ready for pickup!", "order")
        socketio.emit('order_ready', {'order_id': order_id}, to=f"user_{order[0]['user_id']}")
    return jsonify({"success": True})

@app.route("/api/check_active_orders")
@login_required
def check_active_orders():
    ready_notifications = db.execute(
        "SELECT id, message FROM notifications WHERE user_id = ? AND type = 'order' AND read_status = FALSE ORDER BY created_at ASC",
        session["user_id"],
    )
    for notification in ready_notifications:
        db.execute("UPDATE notifications SET read_status = TRUE WHERE id = ?", notification["id"])
    return jsonify({
        "ready_notifications": ready_notifications
    })
@app.route("/update_menu", methods=["GET", "POST"])
@login_required
@admin_required
def update_menu():
    if request.method == "POST":
        item_id = request.form.get("item_id")
        name = request.form.get("name")
        price = request.form.get("price")
        description = request.form.get("description")
        category = request.form.get("category")
        if not item_id :
            flash("Item ID is required.", "warning")
            return redirect("/update_menu")
        if not name or not price or not description or not category:
            flash("all fields (Name, price, description, and category) are required.", "warning")
            return redirect("/update_menu")
        if price and not price.replace('.', '', 1).isdigit():
            flash("Price must be a valid number.", "warning")
            return redirect("/update_menu")
        try:
            db.execute("UPDATE menu_items SET name = ?, price = ?, description = ?, category = ? WHERE id = ?", name, price, description, category, item_id)
            flash("Menu item updated successfully.", "success")
            socketio.emit('menu_updated')
        except Exception as e:
            flash(f"An error occurred while updating the menu item: {e}", "danger")
        return redirect("/update_menu")
    else:
        items = db.execute("SELECT * FROM menu_items WHERE is_available = TRUE")
        return render_template("update_menu.html", items=items)

@app.route("/update_item", methods=["POST"])
@login_required
@admin_required
def update_item():
    item_id = request.form.get("item_id")
    if item_id:
        item = db.execute("SELECT * FROM menu_items WHERE id = ?", item_id)
        if item:
            return render_template("update_item.html", item=item[0])
    return redirect("/update_menu")

@app.route("/remove_item", methods=["POST"])
@login_required
@admin_required
def remove_item():
    item_id = request.form.get("item_id")
    if item_id:
        try:
            db.execute("UPDATE menu_items SET is_available = FALSE WHERE id= ?", item_id )
            flash("Item removed successfully!", "success")
            socketio.emit('menu_updated')
        except Exception as e:
            flash(f"An error occurred while removing the menu item: {e}", "danger")    
    return redirect("/update_menu")
@app.route("/add_item", methods=["GET", "POST"])
@login_required
@admin_required
def add_item():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        category = request.form.get("category")
        price= request.form.get("price")
        if not name or not price or not description or not category:
            flash("All fields (Name, price, description, and category) are required.", "warning")
            return redirect("/add_item")
        if price and not price.replace('.', '', 1).isdigit() or float(price) < 0:
            flash("Price must be a valid positive number.", "warning")
            return redirect("/add_item")
        try:
            exist = db.execute("SELECT id FROM menu_items WHERE name = ?", name)
            if exist:
                db.execute("UPDATE menu_items SET is_available = TRUE, description=?, category=?, price=? WHERE name= ?",
                           description, category, price, name)
                flash("Item added successfully!", "success")
            else:    
                db.execute("INSERT INTO menu_items (name, description, category, price, is_available) VALUES (?, ?, ?, ?, TRUE)",
                            name, description, category, price)
                flash("Item added successfully!", "success")
            socketio.emit('menu_updated')
            return redirect("/update_menu")
        except Exception as e:
            flash(f"An error occurred while adding the item: {e}", "danger")
            return redirect("/add_item")
    return render_template("add_item.html")

@app.route("/api/menu_items")
@login_required
def api_menu_items():
    items = db.execute("SELECT * FROM menu_items WHERE is_available = TRUE")
    return jsonify({"items": items})

@app.route("/add_admin", methods=["GET", "POST"])
@login_required
@admin_required
def add_admin():
    if request.method == "POST":
        if not request.form.get("username"):
            return render_template("register_admin.html", message="Please provide a username")
        if not request.form.get("password"):
            return render_template("register_admin.html", message="Please provide a password")
        if not request.form.get("confirm_password"):
            return render_template("register_admin.html", message="Please confirm your password")
        if request.form.get("password") != request.form.get("confirm_password"):
            return render_template("register_admin.html", message="Passwords do not match")
        user_name = request.form.get("username")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)
        try:
            db.execute('INSERT INTO users (user_name, password_hash, role) Values (?, ?, ?)', user_name, hashed_password, "admin")
            flash("Manager registered successfully!", "success")
            return redirect("/dashboard")
        except Exception:
            return render_template("register_admin.html", message="Username already exists")
            
    else:
        return render_template("register_admin.html")

@app.route('/reports')
@login_required
@admin_required
def reports():
    pending_orders = db.execute("SELECT COUNT(*) AS count FROM orders WHERE status == 'pending' AND DATE(created_at)=DATE('now')")
    if pending_orders:
        pending_orders = pending_orders[0]['count']
    else: 
        pending_orders =0
    preparing_orders = db.execute("SELECT COUNT(*) AS count FROM orders WHERE status == 'preparing' AND DATE(created_at)=DATE('now')")
    if preparing_orders:
        preparing_orders = preparing_orders[0]['count']
    else:
        preparing_orders =0
    completed_orders = db.execute("SELECT COUNT(*) AS count FROM orders WHERE status IN ('completed', 'delivered') AND DATE(created_at)=DATE('now')")
    if completed_orders:
        completed_orders = completed_orders[0]['count']
    else:
        completed_orders = 0    

    total_items = db.execute("SELECT COUNT(*) AS count FROM menu_items is_available = TRUE")[0]['count']
    total_orders = db.execute("SELECT COUNT(*) AS t_orders FROM orders WHERE DATE(created_at) = DATE('now')")[0]['t_orders']
    total_revenue = db.execute("SELECT SUM(total_price) AS total FROM orders WHERE DATE(created_at) = DATE('now')")[0]['total']
    most_ordered = db.execute('''SELECT menu_items.name, SUM(order_items.quantity) AS total_quantity
      FROM order_items JOIN menu_items ON order_items.menu_item_id = menu_items.id 
      JOIN orders ON order_items.order_id = orders.id 
      WHERE DATE(orders.created_at) = DATE('now') 
      GROUP BY order_items.menu_item_id
        ORDER BY total_quantity DESC''')
    top_item = []
    if most_ordered:
        for order in most_ordered:
            if order['total_quantity'] == most_ordered[0]['total_quantity']:
                top_item.append(order['name'])
    else:
        top_item="No orders yet"

    return render_template("reports.html",pending_orders=pending_orders, preparing_orders=preparing_orders,
        completed_orders=completed_orders, total_items=total_items, total_orders=total_orders,
          total_revenue=total_revenue, top_item=top_item)

#use but do not change
stars = ["1", "2", "3", "4", "5"]
@app.route("/reviews")
@login_required
def reviews():
    user_id = session.get('user_id')
    orders = db.execute("SELECT * FROM orders WHERE user_id = ? AND status IN ('delivered') AND not reviewed" , user_id)
    for order in orders:
        order_items = db.execute("SELECT menu_items.name, order_items.price, order_items.quantity FROM order_items JOIN menu_items ON order_items.menu_item_id = menu_items.id WHERE order_items.order_id = ?", order['id'])
        order['items'] = order_items
    return render_template("reviews.html", orders=sorted(orders, key=lambda x: x['created_at'], reverse=True), stars=stars)

@app.route("/submit_review", methods=["POST"])
@login_required
def submit_review():
    user_id = session.get('user_id')
    order_id = request.form.get("order_id")
    review = "no written review"
    rating = request.form.get("rating")
    review = request.form.get("review")
    if not rating:
        flash("Please provide a rating.", "warning")
        return redirect("/reviews")
    if rating not in stars:
        flash("Invalid rating value.", "warning")
        return redirect("/reviews")
    try:
        db.execute("INSERT INTO reviews (user_id, order_id, rating, comment) VALUES (?, ?, ?, ?)", user_id, order_id, int(rating), review)
        db.execute("UPDATE orders SET reviewed = TRUE WHERE id = ?", order_id)
        flash("Thank you for your review!", "success")
    except Exception as e:
        flash(f"An error occurred while submitting your review: {e}", "error")
        return redirect("/reviews")
    return redirect("/reviews")

@app.route("/view_my_reviews")
@login_required
def view_reviews():
    user_id = session.get('user_id')
    reviews = db.execute("SELECT * FROM reviews WHERE user_id = ? ORDER BY created_at DESC", user_id)
    return render_template("view_my_reviews.html", reviews=reviews)

@app.route("/customers_reviews")
@login_required
@admin_required
def customers_reviews():
    reviews = db.execute("SELECT * FROM reviews JOIN users ON reviews.user_id = users.id order by reviews.created_at DESC")
    return render_template("customers_reviews.html", reviews=reviews)

from datetime import datetime, time, timedelta
@app.route('/reserve', methods=['GET', 'POST'])
@login_required
def reserve():
    if request.method == "POST":
        seats = request.form.get("seats")
        date = request.form.get("date")
        start_time = request.form.get("start_time")

        if not seats or not date or not start_time:
            flash("All fields are required!", "error")
            return redirect("/reserve")

        try:
            if int(seats) <=0 or int(seats) > 25:
                flash("Please enter a valid number!", "error")
                return redirect("/reserve")
      
            date_time= datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            if date_time < datetime.now():
                flash("You cannot reserve a table for a past date or time!", "error")
                return redirect("/reserve")

            allowed_date = datetime.now() + timedelta(days=90)
            if date_time > allowed_date:
                flash("You cannot book more than 3 months in advance!", "error")
                return redirect("/reserve")

            start_t = date_time.time()
            if 0 <= start_t.hour < 7:
                flash("Sorry, Reservation cannot start after midnight!", "error")
                return redirect("/reserve")

            end_date_time = date_time + timedelta(hours=3) 
            end_time = end_date_time.strftime("%H:%M")

            start_str = date_time.strftime("%Y-%m-%d %H:%M")
            end_str = end_date_time.strftime("%Y-%m-%d %H:%M")
            
        except ValueError:
            flash("Invalid Input", "error")    
            return redirect("/reserve")

        available_tables = db.execute(
            "SELECT table_number FROM tables " 
        "   WHERE seats >= ? " 
        "   AND table_number NOT IN ("
        "   SELECT table_number FROM reservations "
        "   WHERE status = 'booked' " 
        "   AND (datetime(date || ' ' || start_time) <datetime(?) " 
        "   AND datetime(date || ' ' || start_time, '+3 hours') > datetime(?)) " 
        ") ORDER BY seats ASC ",
          seats, end_str, start_str
        )

        if not available_tables:
            flash("Sorry, no suitable table available at this time", "error")
            return redirect("/reserve")

        table = available_tables[0]["table_number"]
        try:
            db.execute("INSERT INTO reservations (user_id, table_number, seats, date, start_time," \
            "end_time, status) VALUES (?, ?, ?, ?, ?, ?, 'booked')", session['user_id'], table, seats, date, 
            start_time, end_time)
            socketio.emit('reservations_update')
            flash("Table reserved successfully!", "success")
            return redirect("/reserve")
        except Exception as e:
            flash(f"An error occurred while reserving: {e}", "error")
            return redirect("/reserve")

    return render_template("reserve.html")

@app.route("/api/admin/reservations")
@login_required
@admin_required
def api_admin_reservations():   
    reservations = db.execute("SELECT reservations.id, users.user_name, reservations.table_number, " 
        "reservations.seats, reservations.date, reservations.start_time, reservations.end_time, reservations.status" 
        " FROM reservations JOIN users ON reservations.user_id= users.id" 
        " WHERE reservations.status = 'booked'" 
        " ORDER BY reservations.date ASC, reservations.start_time ASC "
    )

    active_reservations =[]
    now = datetime.now()

    for res in reservations:
        try:
            res_start = datetime.strptime(f"{res['date']} {res['start_time']}", "%Y-%m-%d %H:%M")
            res_end = res_start + timedelta(hours=3)

            if res_end > now:
                active_reservations.append(res)
        except ValueError:
                active_reservations.append(res)                                  
    return jsonify(items = active_reservations)

@app.route("/admin/reservations", methods=["GET", "POST"])
@login_required
@admin_required
def admin_reservations():
    if request.method == "POST":
        reservation_id = request.form.get("reservation_id")
        if reservation_id:
            try:
                db.execute("UPDATE reservations SET status ='available' WHERE id = ?", reservation_id)
                socketio.emit('reservations_update')
                return redirect("/api/admin/reservations")
            except Exception as e:
                flash(f"An error occured while updating status {e}", "error")
                return redirect("/admin/reservations")

    reservations = db.execute("SELECT reservations.id, users.user_name, reservations.table_number, " \
        "reservations.seats, reservations.date, reservations.start_time, reservations.end_time, reservations.status" \
        " FROM reservations JOIN users ON reservations.user_id= users.id" \
        " WHERE status = 'booked'" \
        " ORDER BY reservations.date ASC, reservations.start_time ASC ")

    return render_template("admin_reservations.html", reservations = reservations)

@app.route("/my_reservations")
@login_required
def my_reservations():
    reservations = db.execute("SELECT seats, date, start_time, end_time, status " \
    "FROM reservations WHERE user_id = ? ORDER BY status DESC, date ASC, start_time ASC", session['user_id']) 

    return render_template("my_reservations.html", reservations=reservations)

@app.route("/all_orders")
@login_required
@admin_required
def all_orders():
    orders = db.execute("SELECT orders.id, orders.status, orders.total_price, users.user_name FROM orders " \
    "JOIN users ON orders.user_id = users.id " \
    "WHERE orders.created_at >= DATE('now', '-7 days') ORDER BY orders.created_at DESC ")
    for order in orders:
        order_items = db.execute("SELECT menu_items.name, order_items.price, order_items.quantity FROM order_items JOIN menu_items ON order_items.menu_item_id = menu_items.id WHERE order_items.order_id = ?", order['id'])
        order['items'] = order_items
    return render_template("all_orders.html", orders=orders)

@app.route("/remove_admin", methods=["GET", "POST"])
@login_required
@admin_required
def remove_admin():
    if session.get("user_id") == 1:
        if request.method == "POST":
            admin_id = request.form.get("admin_id")
            if not admin_id:
                flash("Please select an admin to remove.", "warning")
                return redirect("/remove_admin")
            try:
                db.execute("UPDATE users SET role = 'user' WHERE id = ?", admin_id)
                socketio.emit('force_logout', {'target_user_id': int(admin_id)})
                flash("Admin removed successfully!", "success")
                return redirect("/remove_admin")
            except Exception as e:
                flash(f"An error occurred while removing the admin: {e}", "danger")
                return redirect("/remove_admin")    
        admins = db.execute("SELECT id, user_name FROM users WHERE role = 'admin' AND id != 1")
        return render_template("remove_admin.html", admins=admins)    
    else:
        flash("Not authorized.", "danger")
        return redirect("/dashboard")
if __name__ == '__main__':
    socketio.run(app, debug=True)
