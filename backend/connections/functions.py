import re
from datetime import datetime
import hashlib
import os

def format_currency(amount):
    """Format a number as currency"""
    if amount is None:
        return "$0.00"
    return f"${float(amount):.2f}"

def format_date(date_str):
    """Format a date string"""
    if isinstance(date_str, str):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    else:
        date_obj = date_str
    return date_obj.strftime('%B %d, %Y')

def validate_email(email):
    """Validate email format"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    """Validate phone number format"""
    phone = re.sub(r'\D', '', phone)
    return len(phone) >= 10

def create_cart_item(product, quantity=1):
    """Create a cart item dictionary from a product"""
    return {
        'product_id': product['product_id'],
        'name': product['name'],
        'price': product['price'],
        'quantity': quantity,
        'image_url': product['image_url'],
        'subtotal': float(product['price']) * quantity
    }

def calculate_cart_totals(cart_items):
    """Calculate subtotal, tax, and total for cart items"""
    subtotal = sum(item['subtotal'] for item in cart_items)
    tax = subtotal * 0.07  
    total = subtotal + tax
    
    return {
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'item_count': sum(item['quantity'] for item in cart_items)
    }

def hash_password(password):
    """Hash a password for storing"""
    salt = "coffeeshop"  
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password(provided_password, stored_password):
    """Verify a stored password against one provided by user"""
    hashed_password = hash_password(provided_password)
    return hashed_password == stored_password

def generate_order_number(order_id):
    """Generate a readable order number"""
    prefix = "AJ"
    timestamp = datetime.now().strftime("%y%m%d")
    return f"{prefix}{timestamp}{order_id:04d}"

def get_order_status_class(status):
    """Get CSS class for order status"""
    status_classes = {
        'pending': 'badge-warning',
        'processing': 'badge-info',
        'completed': 'badge-success',
        'cancelled': 'badge-danger'
    }
    return status_classes.get(status.lower(), 'badge-secondary')

def paginate(items, page, per_page):
    """Paginate a list of items"""
    page = int(page)
    per_page = int(per_page)
    
    total_pages = (len(items) + per_page - 1) // per_page
    
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
        
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        'items': items[start:end],
        'page': page,
        'per_page': per_page,
        'total_items': len(items),
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }

def allowed_file(filename, allowed_extensions):
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def resize_image(file_path, max_width=1200, max_height=1200):
    """Resize an image if it exceeds the maximum dimensions"""
    try:
        from PIL import Image
        
        with Image.open(file_path) as img:
            width, height = img.size
            
            if width > max_width or height > max_height:
                if width > height:
                    new_width = max_width
                    new_height = int(height * (max_width / width))
                else:
                    new_height = max_height
                    new_width = int(width * (max_height / height))
                
                img = img.resize((new_width, new_height), Image.LANCZOS)
                
                img.save(file_path)
                
        return True
    except ImportError:
        print("PIL/Pillow is not installed. Image will not be resized.")
        return False
    except Exception as e:
        print(f"Error resizing image: {e}")
        return False