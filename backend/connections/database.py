import mysql.connector
import os
from mysql.connector import Error
import time

class Database:
    def __init__(self):
        self.host = os.environ.get('DB_HOST', 'localhost')
        self.database = os.environ.get('DB_NAME', 'coffee_shop')
        self.user = os.environ.get('DB_USER', 'root')
        self.password = os.environ.get('DB_PASSWORD', '') 
        self.port = int(os.environ.get('DB_PORT', 3306))
        self.connection = None
        self.max_retries = 3
        self.retry_delay = 2 
        
    def connect(self):
        """Create database connection with retry mechanism"""
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                self.connection = mysql.connector.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    port=self.port,
                    connect_timeout=10
                )
                if self.connection.is_connected():
                    print(f"Connected to MySQL database: {self.database}")
                    return True
            except Error as e:
                last_error = e
                retries += 1
                print(f"Error connecting to MySQL (attempt {retries}/{self.max_retries}): {e}")
                
                if retries < self.max_retries:
                    time.sleep(self.retry_delay)
        
        print(f"Failed to connect to MySQL after {self.max_retries} attempts: {last_error}")
        return False
        
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed")
            
    def execute_query(self, query, params=None):
        """Execute a query and return results with connection retry"""
        max_attempts = 2
        attempt = 0
        
        while attempt < max_attempts:
            try:
                if not self.connection or not self.connection.is_connected():
                    if not self.connect():
                        return None
                
                cursor = self.connection.cursor(dictionary=True)
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                    
                if query.strip().upper().startswith(('SELECT', 'SHOW')):
                    result = cursor.fetchall()
                    cursor.close()
                    return result
                else:
                    self.connection.commit()
                    affected_rows = cursor.rowcount
                    last_id = cursor.lastrowid
                    cursor.close()
                    return {'affected_rows': affected_rows, 'last_id': last_id}
                    
            except mysql.connector.errors.OperationalError as e:
                print(f"MySQL operational error: {e}, attempting to reconnect...")
                self.connection = None
                attempt += 1
                
                if attempt >= max_attempts:
                    print("Max reconnection attempts reached")
                    raise
                    
            except Error as e:
                print(f"Error executing query: {e}")
                return None
    
    def get_all_products(self, sort_by='name', sort_order='ASC', limit=None, offset=None):
        """Get all products from database with sorting and pagination"""
        valid_sort_fields = ['name', 'price', 'category_id', 'created_at']
        valid_sort_orders = ['ASC', 'DESC']
        
        if sort_by not in valid_sort_fields:
            sort_by = 'name'
        if sort_order not in valid_sort_orders:
            sort_order = 'ASC'
            
        query = f"""
        SELECT p.*, c.name as category_name 
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        ORDER BY p.{sort_by} {sort_order}
        """
        
        if limit is not None and offset is not None:
            query += " LIMIT %s OFFSET %s"
            return self.execute_query(query, (limit, offset))
        elif limit is not None:
            query += " LIMIT %s"
            return self.execute_query(query, (limit,))
        else:
            return self.execute_query(query)
    
    def get_products_count(self, category_id=None):
        """Get the total count of products, optionally filtered by category"""
        if category_id:
            query = "SELECT COUNT(*) as count FROM products WHERE category_id = %s"
            result = self.execute_query(query, (category_id,))
        else:
            query = "SELECT COUNT(*) as count FROM products"
            result = self.execute_query(query)
            
        if result:
            return result[0]['count']
        return 0
    
    def search_products(self, search_term, limit=None, offset=None):
        """Search products by name or description"""
        search_pattern = f"%{search_term}%"
        query = """
        SELECT p.*, c.name as category_name 
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.name LIKE %s OR p.description LIKE %s
        ORDER BY p.name
        """
        
        params = (search_pattern, search_pattern)
        
        if limit is not None and offset is not None:
            query += " LIMIT %s OFFSET %s"
            params = params + (limit, offset)
        elif limit is not None:
            query += " LIMIT %s"
            params = params + (limit,)
            
        return self.execute_query(query, params)
    
    def get_featured_products(self, limit=6):
        """Get featured products"""
        query = """
        SELECT p.*, c.name as category_name 
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.is_featured = TRUE
        ORDER BY p.name
        LIMIT %s
        """
        return self.execute_query(query, (limit,))
    
    def get_product_by_id(self, product_id):
        """Get a product by ID"""
        query = """
        SELECT p.*, c.name as category_name 
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.product_id = %s
        """
        results = self.execute_query(query, (product_id,))
        if results:
            return results[0]
        return None
    
    def add_product(self, name, description, price, category_id, image_url=None, is_featured=False, in_stock=True):
        """Add a new product"""
        query = """
        INSERT INTO products (name, description, price, category_id, image_url, is_featured, in_stock)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        result = self.execute_query(
            query, 
            (name, description, price, category_id, image_url, is_featured, in_stock)
        )
        if result:
            return result['last_id']
        return None
    
    def update_product(self, product_id, data):
        """Update product details"""
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        query = f"UPDATE products SET {set_clause} WHERE product_id = %s"
        
        params = list(data.values())
        params.append(product_id)
        
        result = self.execute_query(query, params)
        if result:
            return result['affected_rows']
        return 0
    
    def delete_product(self, product_id):
        """Delete a product"""
        query = "DELETE FROM products WHERE product_id = %s"
        result = self.execute_query(query, (product_id,))
        if result:
            return result['affected_rows']
        return 0
    
    def get_all_categories(self):
        """Get all categories"""
        query = "SELECT * FROM categories ORDER BY name"
        return self.execute_query(query)
    
    def get_category_by_id(self, category_id):
        """Get a category by ID"""
        query = "SELECT * FROM categories WHERE category_id = %s"
        results = self.execute_query(query, (category_id,))
        if results:
            return results[0]
        return None
    
    def add_category(self, name, description=None, image_url=None):
        """Add a new category"""
        query = """
        INSERT INTO categories (name, description, image_url)
        VALUES (%s, %s, %s)
        """
        result = self.execute_query(query, (name, description, image_url))
        if result:
            return result['last_id']
        return None
    
    def update_category(self, category_id, name=None, description=None, image_url=None):
        """Update category details"""
        query = """
        UPDATE categories 
        SET name = COALESCE(%s, name),
            description = COALESCE(%s, description),
            image_url = COALESCE(%s, image_url)
        WHERE category_id = %s
        """
        result = self.execute_query(query, (name, description, image_url, category_id))
        if result:
            return result['affected_rows']
        return 0
    
    def delete_category(self, category_id):
        """Delete a category"""
        query = "DELETE FROM categories WHERE category_id = %s"
        result = self.execute_query(query, (category_id,))
        if result:
            return result['affected_rows']
        return 0
    
    def get_products_by_category(self, category_id, sort_by='name', sort_order='ASC', limit=None, offset=None):
        """Get products by category ID with sorting and pagination"""
        valid_sort_fields = ['name', 'price', 'created_at']
        valid_sort_orders = ['ASC', 'DESC']
        
        if sort_by not in valid_sort_fields:
            sort_by = 'name'
        if sort_order not in valid_sort_orders:
            sort_order = 'ASC'
            
        query = f"""
        SELECT p.*, c.name as category_name 
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.category_id = %s
        ORDER BY p.{sort_by} {sort_order}
        """
        
        params = (category_id,)
        
        if limit is not None and offset is not None:
            query += " LIMIT %s OFFSET %s"
            params = params + (limit, offset)
        elif limit is not None:
            query += " LIMIT %s"
            params = params + (limit,)
            
        return self.execute_query(query, params)
    
    def get_customer_by_email(self, email):
        """Get a customer by email"""
        query = "SELECT * FROM customers WHERE email = %s"
        results = self.execute_query(query, (email,))
        if results:
            return results[0]
        return None
    
    def get_customer_by_id(self, customer_id):
        """Get a customer by ID"""
        query = "SELECT * FROM customers WHERE customer_id = %s"
        results = self.execute_query(query, (customer_id,))
        if results:
            return results[0]
        return None
    
    def add_customer(self, name, email, phone=None, address=None, password=None, role='customer'):
        existing = self.get_customer_by_email(email)
        if existing:
            return existing['customer_id']
            
        query = """
        INSERT INTO customers (name, email, phone, address, password, role, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        result = self.execute_query(query, (name, email, phone, address, password, role))
        if result:
            return result['last_id']
        return None
    
    def update_customer(self, customer_id, data):
        """Update customer details"""
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        query = f"UPDATE customers SET {set_clause} WHERE customer_id = %s"
        
        params = list(data.values())
        params.append(customer_id)
        
        result = self.execute_query(query, params)
        if result:
            return result['affected_rows']
        return 0
    
    def create_order(self, customer_id, total_amount, shipping_address, payment_method):
        """Create a new order"""
        query = """
        INSERT INTO orders (customer_id, total_amount, shipping_address, payment_method)
        VALUES (%s, %s, %s, %s)
        """
        result = self.execute_query(query, (customer_id, total_amount, shipping_address, payment_method))
        if result:
            return result['last_id']
        return None
    
    def add_order_item(self, order_id, product_id, quantity, price):
        """Add item to an order"""
        query = """
        INSERT INTO order_items (order_id, product_id, quantity, price)
        VALUES (%s, %s, %s, %s)
        """
        result = self.execute_query(query, (order_id, product_id, quantity, price))
        if result:
            return result['last_id']
        return None
    
    def get_order_by_id(self, order_id):
        """Get an order by ID"""
        query = """
        SELECT o.*, c.name as customer_name, c.email as customer_email
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = %s
        """
        results = self.execute_query(query, (order_id,))
        if results:
            return results[0]
        return None
    
    def get_order_items(self, order_id):
        """Get items for an order"""
        query = """
        SELECT oi.*, p.name as product_name, p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
        """
        return self.execute_query(query, (order_id,))
    
    def get_customer_orders(self, customer_id):
        """Get orders for a customer"""
        query = """
        SELECT o.*, 
               (SELECT COUNT(*) FROM order_items WHERE order_id = o.order_id) as item_count
        FROM orders o
        WHERE o.customer_id = %s
        ORDER BY o.order_date DESC
        """
        return self.execute_query(query, (customer_id,))
    
    def update_order_status(self, order_id, status):
        """Update order status"""
        valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
        if status not in valid_statuses:
            return 0
            
        query = "UPDATE orders SET status = %s WHERE order_id = %s"
        result = self.execute_query(query, (status, order_id))
        if result:
            return result['affected_rows']
        return 0
    
    def get_recent_orders(self, limit=10):
        """Get recent orders"""
        query = """
        SELECT o.*, c.name as customer_name, c.email as customer_email,
               (SELECT COUNT(*) FROM order_items WHERE order_id = o.order_id) as item_count
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        ORDER BY o.order_date DESC
        LIMIT %s
        """
        return self.execute_query(query, (limit,))
    
    def get_sales_stats(self, days=30):
        """Get sales statistics for the specified number of days"""
        query = """
        SELECT
            COUNT(*) as total_orders,
            SUM(total_amount) as total_sales,
            AVG(total_amount) as average_order_value,
            COUNT(DISTINCT customer_id) as unique_customers
        FROM orders
        WHERE order_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
          AND status != 'cancelled'
        """
        results = self.execute_query(query, (days,))
        if results:
            return results[0]
        return None
    
    def get_top_products(self, limit=5):
        """Get top-selling products"""
        query = """
        SELECT p.product_id, p.name, p.image_url, c.name as category_name,
               SUM(oi.quantity) as total_sold,
               SUM(oi.quantity * oi.price) as total_revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.status != 'cancelled'
        GROUP BY p.product_id
        ORDER BY total_sold DESC
        LIMIT %s
        """
        return self.execute_query(query, (limit,))
    
    def get_sales_by_category(self):
        """Get sales breakdown by category"""
        query = """
        SELECT c.category_id, c.name,
               SUM(oi.quantity) as total_items_sold,
               SUM(oi.quantity * oi.price) as total_revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.status != 'cancelled'
        GROUP BY c.category_id
        ORDER BY total_revenue DESC
        """
        return self.execute_query(query)
    
    def get_sales_by_date(self, days=30):
        """Get daily sales for the specified number of days"""
        query = """
        SELECT DATE(o.order_date) as date,
               COUNT(*) as orders_count,
               SUM(o.total_amount) as daily_sales
        FROM orders o
        WHERE o.order_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
          AND o.status != 'cancelled'
        GROUP BY DATE(o.order_date)
        ORDER BY date
        """
        return self.execute_query(query, (days,))
        
