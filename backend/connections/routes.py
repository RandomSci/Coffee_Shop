from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import os
import uuid
import datetime
from werkzeug.utils import secure_filename
from connections.database import Database
from connections.functions import (
    format_currency, format_date, validate_email, validate_phone,
    create_cart_item, calculate_cart_totals, hash_password, verify_password,
    generate_order_number, get_order_status_class, paginate,
    allowed_file, resize_image
)

routes = Blueprint('routes', __name__)

db = Database()

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'static', 'images', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024 

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('routes.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'admin':
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('routes.index'))
        return f(*args, **kwargs)
    return decorated_function

def get_cart():
    """Get current cart from session"""
    if 'cart' not in session:
        session['cart'] = []
    return session['cart']

def save_cart(cart):
    """Save cart to session"""
    session['cart'] = cart
    session.modified = True

def handle_uploaded_file(file):
    """Process and save an uploaded file"""
    if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex}{ext}"
        
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        resize_image(file_path, max_width=1200, max_height=1200)
        
        return f"/static/images/uploads/{unique_filename}"
    
    return None

@routes.route('/')
def index():
    """Homepage route"""
    featured_products = db.get_featured_products(6)
    categories = db.get_all_categories()
    
    for product in featured_products:
        product['formatted_price'] = format_currency(product['price'])
    
    return render_template(
        'index.html',
        featured_products=featured_products,
        categories=categories
    )

@routes.route('/shop')
def shop():
    """Shop page route"""
    category_id = request.args.get('category')
    search_query = request.args.get('search')
    sort_by = request.args.get('sort', 'name')
    sort_order = request.args.get('order', 'ASC')
    page = request.args.get('page', 1, type=int)
    per_page = 12  
    
    if search_query:
        products = db.search_products(search_query)
        category_name = f"Search results for '{search_query}'"
        current_category = None
    elif category_id:
        category_id = int(category_id)
        products = db.get_products_by_category(category_id, sort_by, sort_order)
        category = db.get_category_by_id(category_id)
        category_name = category['name'] if category else "Products"
        current_category = category_id
    else:
        products = db.get_all_products(sort_by, sort_order)
        category_name = "All Products"
        current_category = None
    
    for product in products:
        product['formatted_price'] = format_currency(product['price'])
    
    paginated = paginate(products, page, per_page)
    
    return render_template(
        'shop.html',
        products=paginated['items'],
        pagination=paginated,
        categories=db.get_all_categories(),
        current_category=current_category,
        category_name=category_name,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order
    )

@routes.route('/product/<int:product_id>')
def product_detail(product_id):
    """Product detail page route"""
    product = db.get_product_by_id(product_id)
    
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('routes.shop'))
    
    product['formatted_price'] = format_currency(product['price'])
    
    related_products = db.get_products_by_category(product['category_id'])
    related_products = [p for p in related_products if p['product_id'] != product_id][:4]
    
    for related in related_products:
        related['formatted_price'] = format_currency(related['price'])
    
    return render_template(
        'product_detail.html',
        product=product,
        related_products=related_products
    )

@routes.route('/cart')
def cart():
    """Shopping cart page route"""
    cart_items = get_cart()
    cart_totals = calculate_cart_totals(cart_items)
    
    return render_template(
        'cart.html',
        cart_items=cart_items,
        cart_totals=cart_totals,
        format_currency=format_currency
    )

@routes.route('/cart/add', methods=['POST'])
def add_to_cart():
    """Add product to cart"""
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    
    if not product_id or quantity < 1:
        flash('Invalid product or quantity', 'danger')
        return redirect(request.referrer or url_for('routes.shop'))
    
    product = db.get_product_by_id(product_id)
    
    if not product:
        flash('Product not found', 'danger')
        return redirect(request.referrer or url_for('routes.shop'))
    
    cart_items = get_cart()
    
    for item in cart_items:
        if item['product_id'] == product_id:
            item['quantity'] += quantity
            item['subtotal'] = float(item['price']) * item['quantity']
            flash(f'Updated {product["name"]} quantity in cart', 'success')
            save_cart(cart_items)
            return redirect(request.form.get('redirect_url') or url_for('routes.cart'))
    
    cart_items.append(create_cart_item(product, quantity))
    save_cart(cart_items)
    
    flash(f'Added {product["name"]} to cart', 'success')
    return redirect(request.form.get('redirect_url') or url_for('routes.cart'))

@routes.route('/cart/update', methods=['POST'])
def update_cart():
    """Update cart quantities via AJAX"""
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    
    if not product_id:
        return jsonify({'error': 'Invalid product ID'}), 400
    
    if quantity < 1:
        return jsonify({'error': 'Quantity must be at least 1'}), 400
    
    cart_items = get_cart()
    
    item_updated = False
    for item in cart_items:
        if item['product_id'] == product_id:
            item['quantity'] = quantity
            item['subtotal'] = float(item['price']) * quantity
            item_updated = True
            break
    
    if not item_updated:
        return jsonify({'error': 'Item not found in cart'}), 404
    
    save_cart(cart_items)
    cart_totals = calculate_cart_totals(cart_items)
    
    return jsonify({
        'success': True,
        'subtotal': format_currency(cart_totals['subtotal']),
        'tax': format_currency(cart_totals['tax']),
        'total': format_currency(cart_totals['total']),
        'item_count': cart_totals['item_count'],
        'item_subtotal': format_currency(float(item['price']) * quantity)
    })

@routes.route('/cart/remove', methods=['POST'])
def remove_from_cart():
    """Remove product from cart via AJAX"""
    product_id = request.form.get('product_id', type=int)
    
    if not product_id:
        return jsonify({'error': 'Invalid product ID'}), 400
    
    cart_items = get_cart()
    
    cart_items = [item for item in cart_items if item['product_id'] != product_id]
    
    save_cart(cart_items)
    cart_totals = calculate_cart_totals(cart_items)
    
    return jsonify({
        'success': True,
        'subtotal': format_currency(cart_totals['subtotal']),
        'tax': format_currency(cart_totals['tax']),
        'total': format_currency(cart_totals['total']),
        'item_count': cart_totals['item_count']
    })

@routes.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart_items = get_cart()
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('routes.shop'))
    
    cart_totals = calculate_cart_totals(cart_items)
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip')
        country = request.form.get('country')
        payment_method = request.form.get('payment_method')
        notes = request.form.get('notes', '')
        
        errors = []
        if not all([name, email, phone, address, city, state, zip_code, country, payment_method]):
            errors.append('Please fill in all required fields')
        if not validate_email(email):
            errors.append('Please enter a valid email address')
        if not validate_phone(phone):
            errors.append('Please enter a valid phone number')
            
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template(
                'checkout.html',
                cart_items=cart_items,
                cart_totals=cart_totals,
                format_currency=format_currency
            )
            
        shipping_address = f"{address}, {city}, {state} {zip_code}, {country}"
        
        if 'user_id' in session:
            customer_id = session['user_id']
            customer_data = {
                'phone': phone,
                'address': shipping_address
            }
            db.update_customer(customer_id, customer_data)
        else:
            customer = db.get_customer_by_email(email)
            if customer:
                customer_id = customer['customer_id']
                customer_data = {
                    'phone': phone,
                    'address': shipping_address
                }
                db.update_customer(customer_id, customer_data)
            else:
                customer_data = {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'address': shipping_address
                }
                customer_id = db.add_customer(**customer_data)
            
        if not customer_id:
            flash('Error creating customer record', 'danger')
            return render_template(
                'checkout.html',
                cart_items=cart_items,
                cart_totals=cart_totals,
                format_currency=format_currency
            )
            
        try:
            order_id = db.create_order(
                customer_id=customer_id,
                total_amount=cart_totals['total'],
                shipping_address=shipping_address,
                payment_method=payment_method
            )
            
            if not order_id:
                flash('Error creating order', 'danger')
                return render_template(
                    'checkout.html',
                    cart_items=cart_items,
                    cart_totals=cart_totals,
                    format_currency=format_currency
                )
                
            for item in cart_items:
                db.add_order_item(
                    order_id=order_id,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    price=item['price']
                )
                
            session['last_order'] = {
                'order_id': order_id,
                'order_number': generate_order_number(order_id),
                'order_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'customer_name': name,
                'shipping_address': shipping_address,
                'payment_method': payment_method,
                'total': cart_totals['total']
            }
                
            session.pop('cart', None)
            
            flash('Your order has been placed successfully!', 'success')
            return redirect(url_for('routes.order_confirmation'))
        except Exception as e:
            print(f"Error processing order: {e}")
            flash('An error occurred while processing your order. Please try again.', 'danger')
            return render_template(
                'checkout.html',
                cart_items=cart_items,
                cart_totals=cart_totals,
                format_currency=format_currency
            )
    
    return render_template(
        'checkout.html',
        cart_items=cart_items,
        cart_totals=cart_totals,
        format_currency=format_currency
    )

@routes.route('/order-confirmation')
def order_confirmation():
    """Order confirmation page route"""
    last_order = session.get('last_order')
    
    if not last_order:
        return redirect(url_for('routes.index'))
    
    last_order['formatted_total'] = format_currency(last_order['total'])
    last_order['formatted_date'] = format_date(last_order['order_date'])
    
    recommended_products = db.get_featured_products(4)
    for product in recommended_products:
        product['formatted_price'] = format_currency(product['price'])
    
    return render_template(
        'order_confirmation.html',
        order=last_order,
        recommended_products=recommended_products
    )

@routes.route('/orders')
@login_required
def orders():
    """Orders history page route with debugging"""
    customer_id = session.get('user_id')
    
    print(f"Current user ID in session: {customer_id}")
    
    if not customer_id:
        flash('Please log in to view your orders', 'warning')
        return redirect(url_for('routes.login'))
    
    debug_query = "SELECT * FROM orders"
    all_orders = db.execute_query(debug_query)
    print(f"All orders in database: {all_orders}")
    
    customer_orders = db.get_customer_orders(customer_id)
    print(f"Orders found for customer {customer_id}: {customer_orders}")
    
    for order in customer_orders:
        order['order_number'] = generate_order_number(order['order_id'])
        order['formatted_date'] = format_date(order['order_date'])
        order['formatted_total'] = format_currency(order['total_amount'])
        order['status_class'] = get_order_status_class(order['status'])
    
    return render_template('orders.html', orders=customer_orders)

@routes.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Order detail page route with proper customer information"""
    customer_id = session.get('user_id')
    
    order = db.get_order_by_id(order_id)
    
    if not order or order['customer_id'] != customer_id:
        flash('Order not found or access denied', 'danger')
        return redirect(url_for('routes.orders'))
    
    order['order_number'] = generate_order_number(order['order_id'])
    order['formatted_date'] = format_date(order['order_date'])
    order['formatted_total'] = format_currency(order['total_amount'])
    order['status_class'] = get_order_status_class(order['status'])
    
    try:
        shipping_parts = order['shipping_address'].split(',')
        order['shipping_address_parts'] = {
            'address': shipping_parts[0].strip() if len(shipping_parts) > 0 else '',
            'city': shipping_parts[1].strip() if len(shipping_parts) > 1 else '',
            'region': shipping_parts[2].strip() if len(shipping_parts) > 2 else '',
            'country': shipping_parts[3].strip() if len(shipping_parts) > 3 else ''
        }
    except Exception as e:
        print(f"Error parsing shipping address: {e}")
        order['shipping_address_parts'] = {
            'address': order['shipping_address'],
            'city': '',
            'region': '',
            'country': ''
        }
    
    customer = db.get_customer_by_id(order['customer_id'])
    if customer:
        order['customer_name'] = customer['name']
    else:
        order['customer_name'] = session.get('user_name', 'Customer')
    
    order_items = db.get_order_items(order_id)
    
    for item in order_items:
        item['formatted_price'] = format_currency(item['price'])
        item['subtotal'] = item['price'] * item['quantity']
        item['formatted_subtotal'] = format_currency(item['subtotal'])
    
    return render_template(
        'order_detail.html',
        order=order,
        order_items=order_items
    )
    
@routes.route('/order/<int:order_id>/details')
@login_required
def order_details_ajax(order_id):
    """AJAX endpoint for order details"""
    customer_id = session.get('user_id')
    
    order = db.get_order_by_id(order_id)
    
    if not order or order['customer_id'] != customer_id:
        return '<div class="alert alert-danger">Order not found or access denied</div>', 403
    
    order['order_number'] = generate_order_number(order['order_id'])
    order['formatted_date'] = format_date(order['order_date'])
    order['formatted_total'] = format_currency(order['total_amount'])
    order['status_class'] = get_order_status_class(order['status'])
    
    customer = db.get_customer_by_id(order['customer_id'])
    if customer:
        order['customer_name'] = customer['name']
    else:
        order['customer_name'] = session.get('user_name', 'Customer')
    
    order_items = db.get_order_items(order_id)
    
    subtotal = 0.0
    for item in order_items:
        item['formatted_price'] = format_currency(item['price'])
        item_price = float(item['price'])
        item_quantity = item['quantity']
        item['subtotal'] = item_price * item_quantity
        item['formatted_subtotal'] = format_currency(item['subtotal'])
        subtotal += item['subtotal']
    
    tax = round(subtotal * 0.07, 2)
    
    return render_template(
        'order_details_partial.html',
        order=order,
        order_items=order_items,
        subtotal=subtotal,
        tax=tax,
        format_currency=format_currency
    )

@routes.route('/about')
def about():
    """About page route"""
    return render_template('about.html')

@routes.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page route"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        if not all([name, email, subject, message]):
            flash('Please fill in all fields', 'danger')
        elif not validate_email(email):
            flash('Please enter a valid email address', 'danger')
        else:
            query = """
            INSERT INTO contact_messages (name, email, subject, message, status, created_at)
            VALUES (%s, %s, %s, %s, 'new', NOW())
            """
            
            db.execute_query(query, (name, email, subject, message))
            
            flash('Thank you for your message! We will get back to you soon.', 'success')
            return redirect(url_for('routes.contact'))
    
    return render_template('contact.html')

@routes.route('/subscribe', methods=['POST'])
def subscribe_newsletter():
    """Newsletter subscription handler"""
    email = request.form.get('email')
    
    if not email or not validate_email(email):
        return jsonify({'error': 'Invalid email address'}), 400
    
    check_query = "SELECT subscriber_id FROM newsletter_subscribers WHERE email = %s AND status = 'active'"
    existing = db.execute_query(check_query, (email,))
    
    if existing:
        return jsonify({
            'success': True, 
            'message': 'You are already subscribed to our newsletter!'
        })
    
    check_unsub_query = "SELECT subscriber_id FROM newsletter_subscribers WHERE email = %s AND status = 'unsubscribed'"
    was_unsubscribed = db.execute_query(check_unsub_query, (email,))
    
    if was_unsubscribed:
        update_query = "UPDATE newsletter_subscribers SET status = 'active', updated_at = NOW() WHERE email = %s"
        db.execute_query(update_query, (email,))
        
        return jsonify({
            'success': True, 
            'message': 'Your subscription has been reactivated!'
        })
    
    insert_query = """
    INSERT INTO newsletter_subscribers (email, status, created_at) 
    VALUES (%s, 'active', NOW())
    """
    result = db.execute_query(insert_query, (email,))
    
    if not result or not result.get('last_id'):
        return jsonify({'error': 'Failed to save subscription'}), 500
    
    return jsonify({
        'success': True, 
        'message': 'Thank you for subscribing to our newsletter!'
    })

@routes.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('routes.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        errors = []
        if not all([name, email, password, confirm_password]):
            errors.append('Please fill in all fields')
        if not validate_email(email):
            errors.append('Please enter a valid email address')
        if password != confirm_password:
            errors.append('Passwords do not match')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long')
            
        existing_user = db.get_customer_by_email(email)
        if existing_user and existing_user.get('password'):
            errors.append('Email address already registered')
            
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')
        
        hashed_password = hash_password(password)
            
        customer_data = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'role': 'customer' 
        }
        
        try:
            customer_id = db.add_customer(**customer_data)
                
            if not customer_id:
                flash('Error creating account', 'danger')
                return render_template('register.html')
                
            session['user_id'] = customer_id
            session['user_name'] = name
            session['user_email'] = email
            session['user_role'] = 'customer'
            
            flash('Registration successful! Welcome to AJ\'s Coffee Buster.', 'success')
            return redirect(url_for('routes.index'))
        except Exception as e:
            print(f"Error during registration: {e}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@routes.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if 'user_id' in session:
        return redirect(url_for('routes.index'))
    
    next_page = request.args.get('next') or url_for('routes.index')
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = db.get_customer_by_email(email)
        
        if not user or not verify_password(password, user.get('password', '')):
            flash('Invalid email or password', 'danger')
            return render_template('login.html', next=next_page)
            
        session['user_id'] = user['customer_id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_role'] = user.get('role', 'customer')
        
        flash('Login successful!', 'success')
        return redirect(next_page)
    
    return render_template('login.html', next=next_page)

@routes.route('/logout')
def logout():
    """User logout"""
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)
    session.pop('user_role', None)
    
    flash('You have been logged out', 'success')
    return redirect(url_for('routes.index'))

@routes.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    customer_id = session.get('user_id')
    customer = db.get_customer_by_id(customer_id)
    
    if not customer:
        session.clear()
        flash('User account not found', 'danger')
        return redirect(url_for('routes.login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        errors = []
        if not name:
            errors.append('Name is required')
            
        if current_password and new_password:
            if not verify_password(current_password, customer.get('password', '')):
                errors.append('Current password is incorrect')
            if new_password != confirm_password:
                errors.append('New passwords do not match')
            if len(new_password) < 8:
                errors.append('New password must be at least 8 characters long')
                
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('profile.html', customer=customer)
            
        update_data = {
            'name': name,
            'phone': phone or customer['phone'],
            'address': address or customer['address']
        }
        
        if current_password and new_password and not errors:
            update_data['password'] = hash_password(new_password)
            
        db.update_customer(customer_id, update_data)
        
        session['user_name'] = name
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('routes.profile'))
    
    return render_template('profile.html', customer=customer)

@routes.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@routes.app_errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500