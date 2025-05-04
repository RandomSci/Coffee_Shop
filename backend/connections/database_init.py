import os
import sys
import hashlib
import uuid
from datetime import datetime

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from backend.connections.database import Database

def hash_password(password):
    """Hash a password for storing"""
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt

def init_database():
    """Initialize database schema and default data"""
    print("Initializing Coffee Shop database...")
    
    db = Database()
    
    if not db.connect():
        print("Failed to connect to MySQL. Please check your database configuration.")
        sys.exit(1)
    
    try:
        db.execute_query("CREATE DATABASE IF NOT EXISTS coffee_shop")
        db.execute_query("USE coffee_shop")
        
        print("Creating tables...")
        
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            image_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            category_id INT,
            image_url VARCHAR(255),
            is_featured BOOLEAN DEFAULT FALSE,
            in_stock BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
        )
        """)
        
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255),
            phone VARCHAR(20),
            address TEXT,
            role ENUM('customer', 'admin') DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('pending', 'processing', 'completed', 'cancelled') DEFAULT 'pending',
            total_amount DECIMAL(10, 2) NOT NULL,
            shipping_address TEXT,
            payment_method VARCHAR(50),
            notes TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE SET NULL
        )
        """)
        
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT,
            product_id INT,
            quantity INT NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL
        )
        """)
        
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            message_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL,
            subject VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            status ENUM('new', 'read', 'replied') DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
            subscriber_id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) UNIQUE NOT NULL,
            status ENUM('active', 'unsubscribed') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        result = db.execute_query("SELECT COUNT(*) as count FROM categories")
        
        if result and result[0]['count'] == 0:
            print("Inserting default data...")
            
            categories = [
                ('Espresso', 'Strong coffee brewed by forcing hot water under pressure through finely ground coffee beans', '/static/images/espresso.jpg'),
                ('Cappuccino', 'Coffee drink with espresso, hot milk, and steamed milk foam', '/static/images/cappuccino.jpg'),
                ('Latte', 'Coffee drink made with espresso and steamed milk', '/static/images/latte.jpg'),
                ('Cold Brew', 'Coffee brewed with cold water over an extended period', '/static/images/cold-brew.jpg'),
                ('Specialty', 'Our signature coffee creations', '/static/images/specialty.jpg')
            ]
            
            for name, description, image_url in categories:
                db.execute_query(
                    "INSERT INTO categories (name, description, image_url) VALUES (%s, %s, %s)",
                    (name, description, image_url)
                )
            
            categories = db.execute_query("SELECT * FROM categories")
            category_map = {cat['name']: cat['category_id'] for cat in categories}
            
            products = [
                ('Classic Espresso', 'Our signature espresso shot with rich crema and a balanced flavor profile. Made from a blend of premium Arabica beans.', 3.50, category_map['Espresso'], '/static/images/classic-espresso.jpg', True),
                ('Double Shot Espresso', 'Double the intensity for coffee lovers. Two shots of our premium espresso for those who need an extra boost.', 4.50, category_map['Espresso'], '/static/images/double-espresso.jpg', False),
                ('Vanilla Cappuccino', 'Classic cappuccino with a hint of vanilla. The perfect balance of espresso, steamed milk, and foam with a sweet vanilla twist.', 5.75, category_map['Cappuccino'], '/static/images/vanilla-cappuccino.jpg', True),
                ('Caramel Cappuccino', 'Sweet caramel blended with our premium cappuccino. A indulgent treat with rich caramel notes.', 5.95, category_map['Cappuccino'], '/static/images/caramel-cappuccino.jpg', False),
                ('Classic Latte', 'Smooth espresso with steamed milk. Our most popular drink for those who enjoy a milder coffee experience.', 5.25, category_map['Latte'], '/static/images/classic-latte.jpg', True),
                ('Hazelnut Latte', 'Rich hazelnut flavored latte. The nutty aroma perfectly complements the espresso and creates a delightful taste.', 5.75, category_map['Latte'], '/static/images/hazelnut-latte.jpg', False),
                ('Overnight Cold Brew', '12-hour brewed cold coffee. Smooth and less acidic than hot coffee, with a naturally sweet flavor profile.', 4.95, category_map['Cold Brew'], '/static/images/overnight-cold-brew.jpg', True),
                ('Vanilla Cold Brew', 'Cold brew infused with vanilla. A refreshing cold coffee with subtle vanilla notes.', 5.25, category_map['Cold Brew'], '/static/images/vanilla-cold-brew.jpg', False),
                ('AJ\'s Coffee Buster', 'Our signature coffee with secret recipe. A unique blend of flavors that will energize your day.', 6.95, category_map['Specialty'], '/static/images/coffee-buster.jpg', True),
                ('Mocha Explosion', 'Rich chocolate and coffee fusion. A decadent drink that combines the best of both worlds - coffee and chocolate lovers rejoice!', 6.75, category_map['Specialty'], '/static/images/mocha-explosion.jpg', False)
            ]
            
            for name, description, price, category_id, image_url, is_featured in products:
                db.execute_query(
                    "INSERT INTO products (name, description, price, category_id, image_url, is_featured) VALUES (%s, %s, %s, %s, %s, %s)",
                    (name, description, price, category_id, image_url, is_featured)
                )
            
            admin_password = hash_password("admin123")
            db.execute_query(
                "INSERT INTO customers (name, email, password, role) VALUES (%s, %s, %s, %s)",
                ("Admin User", "admin@ajscoffee.com", admin_password, "admin")
            )
            
            print("Default data inserted successfully.")
        
        print("Database initialization completed successfully!")
    
    except Exception as e:
        print(f"Error during database initialization: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    init_database()