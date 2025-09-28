"""
Init Database Script - Khởi tạo database với dữ liệu từ books.csv
"""
import os
import sys
from pathlib import Path

# Thêm thư mục hiện tại vào Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from database_manager import db_manager
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_database():
    """Khởi tạo database với dữ liệu từ books.csv"""
    logger.info("🚀 Khởi tạo database với dữ liệu từ books.csv")
    
    try:
        # Kiểm tra file books.csv
        if not os.path.exists('books.csv'):
            logger.error("❌ Không tìm thấy file books.csv")
            return False
        
        logger.info("✅ Tìm thấy file books.csv")
        
        # Kiểm tra database cũ
        if os.path.exists('bookstore.db'):
            logger.info("⚠️ Database cũ đã tồn tại, sẽ migrate dữ liệu mới")
        
        # Khởi tạo database mới
        logger.info("🔧 Khởi tạo database mới...")
        db_manager._init_database()
        
        # Xóa dữ liệu cũ và migrate dữ liệu mới từ books.csv
        logger.info("🗑️ Xóa dữ liệu cũ...")
        try:
            import sqlite3
            with sqlite3.connect('bookstore.db') as conn:
                conn.execute("DELETE FROM books")
                conn.execute("DELETE FROM orders")
                conn.commit()
            logger.info("✅ Đã xóa dữ liệu cũ")
        except Exception as e:
            logger.warning(f"⚠️ Không thể xóa dữ liệu cũ: {e}")
        
        logger.info("📥 Đang migrate dữ liệu từ books.csv...")
        db_manager.migrate_from_csv()
        
        # Kiểm tra kết quả
        books = db_manager.get_all_books()
        logger.info(f"✅ Đã migrate {len(books)} sách vào database")
        
        # Hiển thị một vài sách mẫu
        if books:
            logger.info("📚 Một vài sách mẫu:")
            for i, book in enumerate(books[:5]):
                logger.info(f"  {i+1}. {book.title} - {book.author} ({book.price:,} VND)")
        
        # Thống kê
        stats = db_manager.get_statistics()
        logger.info("📊 Thống kê database:")
        logger.info(f"  • Tổng số sách: {stats.get('total_books', 0)}")
        logger.info(f"  • Tổng số thể loại: {stats.get('total_categories', 0)}")
        logger.info(f"  • Tổng số tác giả: {stats.get('total_authors', 0)}")
        logger.info(f"  • Giá trung bình: {stats.get('average_price', 0):,} VND")
        
        logger.info("🎉 Khởi tạo database hoàn thành!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi khởi tạo database: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test các chức năng database"""
    logger.info("🧪 Test các chức năng database...")
    
    try:
        # Test tìm kiếm
        books = db_manager.search_books("Gilead")
        logger.info(f"✅ Tìm kiếm 'Gilead': {len(books)} kết quả")
        
        # Test tìm theo tác giả
        books = db_manager.get_books_by_author("Sidney Sheldon")
        logger.info(f"✅ Sách của Sidney Sheldon: {len(books)} cuốn")
        
        # Test tìm theo giá
        books = db_manager.get_books_by_price_range(None, 200000)
        logger.info(f"✅ Sách dưới 200,000 VND: {len(books)} cuốn")
        
        # Test thể loại
        categories = db_manager.get_all_categories()
        logger.info(f"✅ Thể loại có sẵn: {len(categories)} loại")
        
        logger.info("✅ Tất cả test đều thành công!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi test database: {e}")
        return False

def main():
    """Hàm chính"""
    logger.info("=" * 60)
    logger.info("KHỞI TẠO DATABASE BOOKSTORE CHATBOT")
    logger.info("=" * 60)
    
    # Khởi tạo database
    if not init_database():
        logger.error("❌ Khởi tạo database thất bại")
        return False
    
    # Test database
    if not test_database():
        logger.error("❌ Test database thất bại")
        return False
    
    logger.info("=" * 60)
    logger.info("✅ HOÀN THÀNH! Database đã sẵn sàng sử dụng")
    logger.info("=" * 60)
    logger.info("💡 Chạy ứng dụng với:")
    logger.info("   streamlit run optimized_app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
