"""
Database Manager - Quản lý cơ sở dữ liệu tối ưu cho BookStore
"""
import pandas as pd
import sqlite3
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import os
from dataclasses import dataclass, asdict
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Book:
    """Cấu trúc dữ liệu sách chuẩn hóa"""
    book_id: str
    title: str
    author: str
    category: str
    price: int
    stock: int
    isbn: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None
    published_year: Optional[int] = None
    thumbnail_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class Order:
    """Cấu trúc dữ liệu đơn hàng chuẩn hóa"""
    order_id: str
    customer_name: str
    phone: str
    address: str
    book_id: str
    quantity: int
    status: str
    total_price: int
    created_at: str
    updated_at: str

class DatabaseManager:
    """Quản lý cơ sở dữ liệu tối ưu với SQLite và caching"""
    
    def __init__(self, db_path: str = "bookstore.db"):
        self.db_path = db_path
        self.cache = {}
        self.cache_ttl = 300  # 5 phút
        self._init_database()
    
    def _init_database(self):
        """Khởi tạo database và tạo bảng nếu chưa có"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Tạo bảng books
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        book_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        category TEXT NOT NULL,
                        price INTEGER NOT NULL,
                        stock INTEGER NOT NULL DEFAULT 0,
                        isbn TEXT,
                        description TEXT,
                        rating REAL,
                        published_year INTEGER,
                        thumbnail_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tạo bảng orders
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id TEXT PRIMARY KEY,
                        customer_name TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        address TEXT NOT NULL,
                        book_id TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        status TEXT NOT NULL DEFAULT 'Pending',
                        total_price INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (book_id) REFERENCES books (book_id)
                    )
                """)
                
                # Tạo index để tối ưu tìm kiếm
                conn.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_books_category ON books(category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_books_price ON books(price)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)")
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def _get_cache_key(self, operation: str, params: Dict) -> str:
        """Tạo cache key từ operation và parameters"""
        key_data = f"{operation}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Kiểm tra cache có còn hiệu lực không"""
        if cache_key not in self.cache:
            return False
        cache_time = self.cache[cache_key].get('timestamp', 0)
        return (datetime.now().timestamp() - cache_time) < self.cache_ttl
    
    def _set_cache(self, cache_key: str, data: Any):
        """Lưu data vào cache"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now().timestamp()
        }
    
    def _get_cache(self, cache_key: str) -> Any:
        """Lấy data từ cache"""
        return self.cache[cache_key]['data']
    
    def migrate_from_csv(self, books_csv: str = "books.csv", orders_csv: str = "orders.csv"):
        """Migrate dữ liệu từ CSV sang SQLite"""
        try:
            # Migrate books
            if os.path.exists(books_csv):
                books_df = pd.read_csv(books_csv, encoding="utf-8-sig")
                books_data = []
                
                for _, row in books_df.iterrows():
                    book = Book(
                        book_id=str(row.get('book_id', f"book_{len(books_data) + 1}")),
                        title=str(row.get('title', '')).strip(),
                        author=str(row.get('author', '')).strip(),
                        category=str(row.get('category', 'Unknown')).strip(),
                        price=int(row.get('price', 0)) if pd.notna(row.get('price')) else 0,
                        stock=int(row.get('stock', 10)) if pd.notna(row.get('stock')) else 10,
                        isbn=str(row.get('book_id', '')) if pd.notna(row.get('book_id')) else None,
                        description=None,  # books.csv không có description
                        rating=None,  # books.csv không có rating
                        published_year=None,  # books.csv không có published_year
                        thumbnail_url=None  # books.csv không có thumbnail_url
                    )
                    books_data.append(book)
                
                self.bulk_insert_books(books_data)
                logger.info(f"Migrated {len(books_data)} books from CSV")
            
            # Migrate orders
            if os.path.exists(orders_csv):
                orders_df = pd.read_csv(orders_csv, encoding="utf-8-sig")
                orders_data = []
                
                for _, row in orders_df.iterrows():
                    # Tính total_price
                    book = self.get_book_by_id(str(row.get('book_id', '')))
                    total_price = book.price * int(row.get('quantity', 1)) if book else 0
                    
                    order = Order(
                        order_id=str(row.get('order_id', f"order_{len(orders_data) + 1}")),
                        customer_name=str(row.get('customer_name', 'Khách hàng')).strip(),
                        phone=str(row.get('phone', '')).strip(),
                        address=str(row.get('address', '')).strip(),
                        book_id=str(row.get('book_id', '')),
                        quantity=int(row.get('quantity', 1)),
                        status=str(row.get('status', 'Pending')).strip(),
                        total_price=total_price,
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat()
                    )
                    orders_data.append(order)
                
                self.bulk_insert_orders(orders_data)
                logger.info(f"Migrated {len(orders_data)} orders from CSV")
                
        except Exception as e:
            logger.error(f"Error migrating from CSV: {e}")
            raise
    
    def get_all_books(self, use_cache: bool = True) -> List[Book]:
        """Lấy tất cả sách với caching"""
        cache_key = self._get_cache_key("get_all_books", {})
        
        if use_cache and self._is_cache_valid(cache_key):
            return self._get_cache(cache_key)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM books ORDER BY title")
                books = [Book(**dict(row)) for row in cursor.fetchall()]
                
                if use_cache:
                    self._set_cache(cache_key, books)
                
                return books
        except Exception as e:
            logger.error(f"Error getting all books: {e}")
            return []
    
    def get_book_by_id(self, book_id: str) -> Optional[Book]:
        """Lấy sách theo ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM books WHERE book_id = ?", (book_id,))
                row = cursor.fetchone()
                return Book(**dict(row)) if row else None
        except Exception as e:
            logger.error(f"Error getting book by ID {book_id}: {e}")
            return None
    
    def search_books(self, query: str, search_fields: List[str] = None) -> List[Book]:
        """Tìm kiếm sách theo nhiều tiêu chí"""
        if search_fields is None:
            search_fields = ['title', 'author', 'category']
        
        cache_key = self._get_cache_key("search_books", {"query": query, "fields": search_fields})
        
        if self._is_cache_valid(cache_key):
            return self._get_cache(cache_key)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Tạo điều kiện tìm kiếm
                conditions = []
                params = []
                
                for field in search_fields:
                    conditions.append(f"{field} LIKE ?")
                    params.append(f"%{query}%")
                
                sql = f"SELECT * FROM books WHERE {' OR '.join(conditions)} ORDER BY title"
                cursor = conn.execute(sql, params)
                books = [Book(**dict(row)) for row in cursor.fetchall()]
                
                self._set_cache(cache_key, books)
                return books
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return []
    
    def get_books_by_price_range(self, min_price: Optional[int] = None, max_price: Optional[int] = None) -> List[Book]:
        """Lấy sách theo khoảng giá"""
        cache_key = self._get_cache_key("get_books_by_price_range", {"min": min_price, "max": max_price})
        
        if self._is_cache_valid(cache_key):
            return self._get_cache(cache_key)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                conditions = []
                params = []
                
                if min_price is not None:
                    conditions.append("price >= ?")
                    params.append(min_price)
                
                if max_price is not None:
                    conditions.append("price <= ?")
                    params.append(max_price)
                
                sql = "SELECT * FROM books"
                if conditions:
                    sql += f" WHERE {' AND '.join(conditions)}"
                sql += " ORDER BY price"
                
                cursor = conn.execute(sql, params)
                books = [Book(**dict(row)) for row in cursor.fetchall()]
                
                self._set_cache(cache_key, books)
                return books
        except Exception as e:
            logger.error(f"Error getting books by price range: {e}")
            return []
    
    def get_books_by_category(self, category: str) -> List[Book]:
        """Lấy sách theo thể loại"""
        cache_key = self._get_cache_key("get_books_by_category", {"category": category})
        
        if self._is_cache_valid(cache_key):
            return self._get_cache(cache_key)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM books WHERE category LIKE ? ORDER BY title", (f"%{category}%",))
                books = [Book(**dict(row)) for row in cursor.fetchall()]
                
                self._set_cache(cache_key, books)
                return books
        except Exception as e:
            logger.error(f"Error getting books by category: {e}")
            return []
    
    def get_books_by_author(self, author: str) -> List[Book]:
        """Lấy sách theo tác giả"""
        cache_key = self._get_cache_key("get_books_by_author", {"author": author})
        
        if self._is_cache_valid(cache_key):
            return self._get_cache(cache_key)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM books WHERE author LIKE ? ORDER BY title", (f"%{author}%",))
                books = [Book(**dict(row)) for row in cursor.fetchall()]
                
                self._set_cache(cache_key, books)
                return books
        except Exception as e:
            logger.error(f"Error getting books by author: {e}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """Lấy tất cả thể loại sách"""
        cache_key = self._get_cache_key("get_all_categories", {})
        
        if self._is_cache_valid(cache_key):
            return self._get_cache(cache_key)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT DISTINCT category FROM books ORDER BY category")
                categories = [row[0] for row in cursor.fetchall()]
                
                self._set_cache(cache_key, categories)
                return categories
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    def update_book_stock(self, book_id: str, new_stock: int) -> bool:
        """Cập nhật tồn kho sách"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE books SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE book_id = ?",
                    (new_stock, book_id)
                )
                conn.commit()
                
                # Xóa cache liên quan
                self._clear_related_cache()
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating book stock: {e}")
            return False
    
    def create_order(self, order: Order) -> bool:
        """Tạo đơn hàng mới"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Kiểm tra tồn kho
                book = self.get_book_by_id(order.book_id)
                if not book or book.stock < order.quantity:
                    return False
                
                # Tạo đơn hàng
                cursor = conn.execute("""
                    INSERT INTO orders (order_id, customer_name, phone, address, book_id, quantity, status, total_price, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order.order_id, order.customer_name, order.phone, order.address,
                    order.book_id, order.quantity, order.status, order.total_price,
                    order.created_at, order.updated_at
                ))
                
                # Cập nhật tồn kho
                new_stock = book.stock - order.quantity
                conn.execute(
                    "UPDATE books SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE book_id = ?",
                    (new_stock, order.book_id)
                )
                
                conn.commit()
                
                # Xóa cache liên quan
                self._clear_related_cache()
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return False
    
    def get_orders_by_customer(self, phone: str) -> List[Order]:
        """Lấy đơn hàng theo số điện thoại khách hàng"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM orders WHERE phone = ? ORDER BY created_at DESC", (phone,))
                return [Order(**dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting orders by customer: {e}")
            return []
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Cập nhật trạng thái đơn hàng"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
                    (status, order_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False
    
    def bulk_insert_books(self, books: List[Book]):
        """Thêm nhiều sách cùng lúc"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                books_data = [asdict(book) for book in books]
                df = pd.DataFrame(books_data)
                df.to_sql('books', conn, if_exists='append', index=False)
                conn.commit()
                self._clear_related_cache()
        except Exception as e:
            logger.error(f"Error bulk inserting books: {e}")
            raise
    
    def bulk_insert_orders(self, orders: List[Order]):
        """Thêm nhiều đơn hàng cùng lúc"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                orders_data = [asdict(order) for order in orders]
                df = pd.DataFrame(orders_data)
                df.to_sql('orders', conn, if_exists='append', index=False)
                conn.commit()
                self._clear_related_cache()
        except Exception as e:
            logger.error(f"Error bulk inserting orders: {e}")
            raise
    
    def _clear_related_cache(self):
        """Xóa cache liên quan khi có thay đổi dữ liệu"""
        self.cache.clear()
        logger.info("Cache cleared due to data changes")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê tổng quan"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}
                
                # Thống kê sách
                cursor = conn.execute("SELECT COUNT(*) FROM books")
                stats['total_books'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT category) FROM books")
                stats['total_categories'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT author) FROM books")
                stats['total_authors'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT AVG(price) FROM books")
                stats['average_price'] = round(cursor.fetchone()[0] or 0, 2)
                
                cursor = conn.execute("SELECT SUM(stock) FROM books")
                stats['total_stock'] = cursor.fetchone()[0] or 0
                
                # Thống kê đơn hàng
                cursor = conn.execute("SELECT COUNT(*) FROM orders")
                stats['total_orders'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'")
                stats['pending_orders'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT SUM(total_price) FROM orders WHERE status = 'Completed'")
                stats['total_revenue'] = cursor.fetchone()[0] or 0
                
                return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

# Singleton instance
db_manager = DatabaseManager()
