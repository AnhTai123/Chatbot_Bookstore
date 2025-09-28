"""
Setup Script - Khởi tạo và cấu hình hệ thống BookStore Chatbot
"""
import os
import sys
import logging
from pathlib import Path

# Thêm thư mục hiện tại vào Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from database_manager import db_manager
from chatbot import OptimizedChatbot

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bookstore_setup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Kiểm tra các thư viện cần thiết"""
    logger.info("Kiểm tra dependencies...")
    
    required_packages = [
        'streamlit',
        'pandas',
        'sqlite3',
        'langchain_community'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'sqlite3':
                import sqlite3
            elif package == 'langchain_community':
                from langchain_community.document_loaders import TextLoader
            else:
                __import__(package)
            logger.info(f"✓ {package} đã được cài đặt")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"✗ {package} chưa được cài đặt")
    
    if missing_packages:
        logger.error(f"Các package còn thiếu: {', '.join(missing_packages)}")
        logger.info("Chạy lệnh sau để cài đặt:")
        logger.info(f"pip install {' '.join(missing_packages)}")
        return False
    
    logger.info("Tất cả dependencies đã sẵn sàng!")
    return True

def check_data_files():
    """Kiểm tra các file dữ liệu"""
    logger.info("Kiểm tra file dữ liệu...")
    
    data_files = {
        'books.csv': 'Dữ liệu sách chính',
        'orders.csv': 'Dữ liệu đơn hàng',
        'tagged_description.txt': 'Mô tả sách có tag (tùy chọn)'
    }
    
    missing_files = []
    
    for filename, description in data_files.items():
        if os.path.exists(filename):
            logger.info(f"✓ {filename} - {description}")
        else:
            missing_files.append(filename)
            logger.warning(f"✗ {filename} - {description} (không tìm thấy)")
    
    if missing_files:
        logger.warning(f"Các file dữ liệu còn thiếu: {', '.join(missing_files)}")
        logger.info("Hệ thống sẽ tạo database trống nếu cần")
    
    return len(missing_files) == 0

def initialize_database():
    """Khởi tạo database"""
    logger.info("Khởi tạo database...")
    
    try:
        # Khởi tạo database
        db_manager._init_database()
        logger.info("✓ Database đã được khởi tạo")
        
        # Migrate dữ liệu từ CSV
        if os.path.exists('books.csv'):
            logger.info("Đang migrate dữ liệu từ books.csv...")
            db_manager.migrate_from_csv()
            logger.info("✓ Dữ liệu đã được migrate từ books.csv")
        else:
            logger.warning("Không tìm thấy file books.csv để migrate")
        
        # Kiểm tra dữ liệu
        books_count = len(db_manager.get_all_books())
        orders_count = len(db_manager.get_orders_by_customer("test"))  # Test query
        
        logger.info(f"✓ Database có {books_count} sách")
        logger.info(f"✓ Database có {orders_count} đơn hàng (test)")
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo database: {e}")
        return False

def test_chatbot():
    """Test chatbot"""
    logger.info("Test chatbot...")
    
    try:
        # Test các chức năng cơ bản
        test_queries = [
            "Xin chào",
            "Cửa hàng có những loại sách gì?",
            "Gợi ý sách hay",
            "Giá dưới 100000"
        ]
        
        for query in test_queries:
            chatbot = OptimizedChatbot()
            response = chatbot.process_message(query)
            if response.get("message"):
                logger.info(f"✓ Test query '{query}' - OK")
            else:
                logger.warning(f"✗ Test query '{query}' - Failed")
        
        logger.info("✓ Chatbot test hoàn thành")
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi test chatbot: {e}")
        return False

def create_sample_data():
    """Tạo dữ liệu mẫu nếu cần"""
    logger.info("Tạo dữ liệu mẫu...")
    
    try:
        from database_manager import Book, Order
        from datetime import datetime
        
        # Kiểm tra xem đã có dữ liệu chưa
        existing_books = db_manager.get_all_books()
        if existing_books:
            logger.info(f"Đã có {len(existing_books)} sách, bỏ qua tạo dữ liệu mẫu")
            return True
        
        # Tạo dữ liệu mẫu
        sample_books = [
            Book(
                book_id="9780002005883",
                title="Gilead",
                author="Marilynne Robinson",
                category="Fiction",
                price=150000,
                stock=10,
                isbn="9780002005883",
                description="A novel about family, faith, and forgiveness",
                rating=4.2,
                published_year=2004
            ),
            Book(
                book_id="9780006178736",
                title="Rage of Angels",
                author="Sidney Sheldon",
                category="Fiction",
                price=120000,
                stock=15,
                isbn="9780006178736",
                description="A thrilling story of ambition and revenge",
                rating=4.0,
                published_year=1993
            ),
            Book(
                book_id="9780006472612",
                title="Master of the Game",
                author="Sidney Sheldon",
                category="Adventure",
                price=130000,
                stock=8,
                isbn="9780006472612",
                description="An epic tale of power and family",
                rating=4.1,
                published_year=1982
            )
        ]
        
        db_manager.bulk_insert_books(sample_books)
        logger.info(f"✓ Đã tạo {len(sample_books)} sách mẫu")
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo dữ liệu mẫu: {e}")
        return False

def setup_logging():
    """Cấu hình logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Cấu hình logging cho các module
    logging.getLogger('database_manager').setLevel(logging.INFO)
    logging.getLogger('nlp_processor').setLevel(logging.INFO)
    logging.getLogger('session_manager').setLevel(logging.INFO)
    logging.getLogger('optimized_chatbot').setLevel(logging.INFO)

def main():
    """Hàm chính setup"""
    logger.info("=" * 50)
    logger.info("KHỞI TẠO HỆ THỐNG BOOKSTORE CHATBOT")
    logger.info("=" * 50)
    
    # Cấu hình logging
    setup_logging()
    
    # Kiểm tra dependencies
    if not check_dependencies():
        logger.error("Setup thất bại: Thiếu dependencies")
        return False
    
    # Kiểm tra file dữ liệu
    check_data_files()
    
    # Khởi tạo database
    if not initialize_database():
        logger.error("Setup thất bại: Không thể khởi tạo database")
        return False
    
    # Tạo dữ liệu mẫu nếu cần (chỉ khi không có dữ liệu từ CSV)
    if not os.path.exists('books.csv'):
        create_sample_data()
    
    # Test chatbot
    if not test_chatbot():
        logger.error("Setup thất bại: Chatbot test không thành công")
        return False
    
    logger.info("=" * 50)
    logger.info("SETUP HOÀN THÀNH THÀNH CÔNG!")
    logger.info("=" * 50)
    logger.info("Chạy ứng dụng với lệnh: streamlit run optimized_app.py")
    logger.info("Hoặc chạy ứng dụng cũ: streamlit run app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
