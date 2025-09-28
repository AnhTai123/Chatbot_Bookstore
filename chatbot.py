"""
Optimized Chatbot - Chatbot tối ưu cho BookStore với các tính năng nâng cao
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import random

from database_manager import db_manager, Book, Order
from nlp_processor import nlp_processor, IntentType, IntentResult, SentimentType
from session_manager import session_manager, order_flow_manager, OrderState

logger = logging.getLogger(__name__)

class OptimizedChatbot:
    """Chatbot tối ưu với các tính năng nâng cao"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.nlp_processor = nlp_processor
        self.session_manager = session_manager
        self.order_flow_manager = order_flow_manager
        
        # Cập nhật dữ liệu sách cho NLP processor
        self._update_books_data()
    
    def _update_books_data(self):
        """Cập nhật dữ liệu sách cho NLP processor"""
        try:
            books = self.db_manager.get_all_books()
            books_data = [{"title": book.title, "author": book.author, "category": book.category} for book in books]
            self.nlp_processor.update_books_data(books_data)
        except Exception as e:
            logger.error(f"Error updating books data: {e}")
    
    def process_message(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """Xử lý tin nhắn từ người dùng"""
        try:
            # Tạo session nếu chưa có
            if not session_id:
                session_id = self.session_manager.create_session()
            
            # Lấy session
            session = self.session_manager.get_session(session_id)
            if not session:
                return {"error": "Session không hợp lệ"}
            
            # Thêm tin nhắn vào lịch sử
            self.session_manager.add_message_to_history(session_id, "user", user_input)
            
            # Xử lý dựa trên trạng thái đặt hàng
            if session.order_state != OrderState.NONE:
                response = self._handle_order_flow(user_input, session_id)
            else:
                response = self._handle_normal_conversation(user_input, session_id)
            
            # Thêm phản hồi vào lịch sử
            self.session_manager.add_message_to_history(session_id, "assistant", response["message"])
            
            # Đảm bảo response có key "message"
            if "message" not in response:
                logger.error(f"Response missing 'message' key: {response}")
                response["message"] = "Xin lỗi, có lỗi xảy ra trong quá trình xử lý."
            
            return {
                "session_id": session_id,
                "message": response["message"],
                "intent": response.get("intent"),
                "data": response.get("data", {}),
                "suggestions": response.get("suggestions", [])
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "session_id": session_id,
                "message": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.",
                "error": str(e)
            }
    
    def _handle_order_flow(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """Xử lý quy trình đặt hàng"""
        order_state = self.session_manager.get_order_state(session_id)
        
        if order_state == OrderState.WAITING_QUANTITY:
            return self._handle_quantity_input(user_input, session_id)
        elif order_state == OrderState.WAITING_ADDRESS_PHONE:
            return self._handle_address_phone_input(user_input, session_id)
        elif order_state == OrderState.CONFIRMING_ORDER:
            return self._handle_order_confirmation(user_input, session_id)
        else:
            # Reset về trạng thái bình thường
            self.session_manager.clear_order_data(session_id)
            return self._handle_normal_conversation(user_input, session_id)
    
    def _handle_quantity_input(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """Xử lý nhập số lượng"""
        quantity = self.nlp_processor.entity_extractor.extract_quantity(user_input)
        
        if quantity and quantity > 0:
            result = self.order_flow_manager.process_quantity(session_id, quantity)
            return {
                "message": result["message"],
                "intent": "order_quantity",
                "data": result.get("order_data", {})
            }
        else:
            return {
                "message": "Vui lòng nhập số lượng hợp lệ (ví dụ: '2').",
                "intent": "order_quantity_error"
            }
    
    def _handle_address_phone_input(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """Xử lý nhập địa chỉ và số điện thoại"""
        phone = self.nlp_processor.entity_extractor.extract_phone_number(user_input)
        address = self.nlp_processor.entity_extractor.extract_address(user_input)
        
        if phone and address:
            result = self.order_flow_manager.process_address_phone(session_id, address, phone)
            return {
                "message": result["message"],
                "intent": "order_address_phone",
                "data": result.get("order_data", {})
            }
        else:
            return {
                "message": "Vui lòng nhập địa chỉ và số điện thoại hợp lệ (ví dụ: '123 Hà Nội, 0987654321').",
                "intent": "order_address_phone_error"
            }
    
    def _handle_order_confirmation(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """Xử lý xác nhận đơn hàng"""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['có', 'yes', 'đồng ý', 'ok', 'xác nhận']):
            result = self.order_flow_manager.confirm_order(session_id, True)
            
            if result.get("action") == "process_order":
                # Xử lý đơn hàng
                order_result = self._process_order(session_id)
                final_result = self.order_flow_manager.complete_order(session_id, order_result)
                return {
                    "message": final_result["message"],
                    "intent": "order_completed" if final_result.get("action") == "order_completed" else "order_failed",
                    "data": order_result.get("order_data", {})
                }
            
            return {
                "message": result["message"],
                "intent": "order_confirmed"
            }
        elif any(word in user_input_lower for word in ['không', 'no', 'huỷ', 'hủy', 'cancel']):
            result = self.order_flow_manager.confirm_order(session_id, False)
            return {
                "message": result["message"],
                "intent": "order_cancelled"
            }
        else:
            return {
                "message": "Vui lòng trả lời 'có' để xác nhận hoặc 'không' để hủy.",
                "intent": "order_confirmation_error"
            }
    
    def _process_order(self, session_id: str) -> Dict[str, Any]:
        """Xử lý tạo đơn hàng"""
        try:
            order_data = self.session_manager.get_order_data(session_id)
            if not order_data:
                return {"success": False, "message": "Không tìm thấy thông tin đơn hàng"}
            
            # Tạo đơn hàng mới
            order = Order(
                order_id=f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
                customer_name=order_data.customer_name,
                phone=order_data.phone,
                address=order_data.address,
                book_id=order_data.book_id,
                quantity=order_data.quantity,
                status="Pending",
                total_price=order_data.total_price,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            # Lưu đơn hàng
            success = self.db_manager.create_order(order)
            
            if success:
                return {
                    "success": True,
                    "message": f"Đơn hàng {order.order_id} đã được tạo thành công! Tổng tiền: {self._format_currency(order.total_price)}",
                    "order_data": {
                        "order_id": order.order_id,
                        "total_price": order.total_price,
                        "status": order.status
                    }
                }
            else:
                return {"success": False, "message": "Không thể tạo đơn hàng. Vui lòng kiểm tra lại thông tin."}
                
        except Exception as e:
            logger.error(f"Error processing order: {e}")
            return {"success": False, "message": f"Có lỗi xảy ra: {str(e)}"}
    
    def _handle_normal_conversation(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """Xử lý hội thoại bình thường với context awareness"""
        # Phân tích intent với context
        intent_result = self.nlp_processor.process_input(user_input, session_id)
        
        # Debug logging
        logger.info(f"Intent: {intent_result.intent}, Confidence: {intent_result.confidence}, Params: {intent_result.parameters}")
        
        # Xử lý theo intent
        if intent_result.intent == IntentType.ORDER:
            return self._handle_order_intent(intent_result, session_id)
        elif intent_result.intent == IntentType.QUERY:
            return self._handle_query_intent(intent_result, session_id)
        elif intent_result.intent == IntentType.SEARCH_BY_TITLE:
            return self._handle_search_by_title(intent_result, session_id)
        elif intent_result.intent == IntentType.SEARCH_BY_AUTHOR:
            return self._handle_search_by_author(intent_result, session_id)
        elif intent_result.intent == IntentType.SEARCH_BY_CATEGORY:
            return self._handle_search_by_category(intent_result, session_id)
        elif intent_result.intent == IntentType.SEARCH_BY_PRICE:
            return self._handle_search_by_price(intent_result, session_id)
        elif intent_result.intent == IntentType.RECOMMEND:
            return self._handle_recommend(intent_result, session_id)
        elif intent_result.intent == IntentType.RECOMMEND_BY_PRICE:
            return self._handle_recommend_by_price(intent_result, session_id)
        elif intent_result.intent == IntentType.LIST_CATEGORIES:
            return self._handle_list_categories(intent_result, session_id)
        elif intent_result.intent == IntentType.CHECK_STOCK:
            return self._handle_check_stock(intent_result, session_id)
        elif intent_result.intent == IntentType.GREETING:
            return self._handle_greeting(intent_result, session_id)
        elif intent_result.intent == IntentType.GOODBYE:
            return self._handle_goodbye(intent_result, session_id)
        elif intent_result.intent == IntentType.HELP:
            return self._handle_help(intent_result, session_id)
        else:
            return self._handle_unknown_intent(intent_result, session_id)
    
    def _handle_order_intent(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý intent đặt hàng"""
        book_title = intent_result.parameters.get("book_title")
        
        if not book_title:
            return {
                "message": "Không tìm thấy tên sách. Vui lòng thử lại (ví dụ: 'Đặt mua Gilead').",
                "intent": "order_error"
            }
        
        # Tìm sách
        books = self.db_manager.search_books(book_title)
        if not books:
            return {
                "message": f"Không tìm thấy sách '{book_title}'. Vui lòng kiểm tra lại tên sách.",
                "intent": "order_error"
            }
        
        # Lấy sách đầu tiên (có thể cải thiện bằng cách chọn sách phù hợp nhất)
        book = books[0]
        
        if book.stock <= 0:
            return {
                "message": f"Sách '{book.title}' hiện đã hết hàng.",
                "intent": "order_error"
            }
        
        # Bắt đầu quy trình đặt hàng
        book_data = {
            "book_id": book.book_id,
            "title": book.title,
            "price": book.price
        }
        
        result = self.order_flow_manager.start_order(session_id, book_data)
        return {
            "message": result["message"],
            "intent": "order_started",
            "data": result.get("order_data", {})
        }
    
    def _handle_query_intent(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý intent truy vấn thông tin"""
        book_title = intent_result.parameters.get("book_title")
        is_price_only = intent_result.parameters.get("is_price_only", False)
        is_stock_only = intent_result.parameters.get("is_stock_only", False)
        
        if not book_title:
            return {
                "message": "Không tìm thấy tên sách trong câu hỏi. Vui lòng thử lại (ví dụ: 'Giá sách Gilead').",
                "intent": "query_error"
            }
        
        # Tìm sách
        books = self.db_manager.search_books(book_title)
        if not books:
            return {
                "message": f"Không tìm thấy sách '{book_title}'.",
                "intent": "query_error"
            }
        
        book = books[0]
        
        if is_price_only:
            message = f"Giá sách '{book.title}': {self._format_currency(book.price)}"
        elif is_stock_only:
            message = f"Sách '{book.title}' còn {book.stock} cuốn trong kho."
        else:
            message = f"Thông tin sách '{book.title}':\n• Tác giả: {book.author}\n• Giá: {self._format_currency(book.price)}\n• Tồn kho: {book.stock} cuốn\n• Thể loại: {book.category}"
            if book.rating:
                message += f"\n• Đánh giá: {book.rating}/5"
        
        # Lấy smart suggestions
        smart_suggestions = self.nlp_processor.get_smart_suggestions(session_id, IntentType.QUERY)
        
        return {
            "message": message,
            "intent": "query_success",
            "data": {"book": book.__dict__},
            "suggestions": smart_suggestions
        }
    
    def _handle_search_by_title(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý tìm kiếm theo tên sách"""
        book_title = intent_result.parameters.get("book_title")
        
        if not book_title:
            return {
                "message": "Vui lòng chỉ định tên sách cần tìm.",
                "intent": "search_error"
            }
        
        books = self.db_manager.search_books(book_title)
        
        if not books:
            return {
                "message": f"Không tìm thấy sách nào có tên chứa '{book_title}'.",
                "intent": "search_error"
            }
        
        # Giới hạn kết quả
        max_results = 5
        shown_books = books[:max_results]
        remaining = len(books) - max_results
        
        message = f"Tìm thấy {len(books)} sách có tên chứa '{book_title}':\n\n"
        for i, book in enumerate(shown_books, 1):
            message += f"{i}. {book.title} - {book.author} ({self._format_currency(book.price)})\n"
        
        if remaining > 0:
            message += f"\n... và còn {remaining} sách khác."
        
        # Lấy smart suggestions
        smart_suggestions = self.nlp_processor.get_smart_suggestions(session_id, IntentType.SEARCH_BY_TITLE)
        
        return {
            "message": message,
            "intent": "search_success",
            "data": {"books": [book.__dict__ for book in shown_books]},
            "suggestions": smart_suggestions
        }
    
    def _handle_search_by_author(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý tìm kiếm theo tác giả"""
        author = intent_result.parameters.get("author")
        
        if not author:
            return {
                "message": "Vui lòng chỉ định tác giả (ví dụ: 'Sidney Sheldon').",
                "intent": "search_error"
            }
        
        books = self.db_manager.get_books_by_author(author)
        
        if not books:
            return {
                "message": f"Không tìm thấy sách nào của tác giả '{author}'.",
                "intent": "search_error"
            }
        
        # Giới hạn kết quả
        max_results = 5
        shown_books = books[:max_results]
        remaining = len(books) - max_results
        
        message = f"Sách của tác giả '{author}':\n\n"
        for i, book in enumerate(shown_books, 1):
            message += f"{i}. {book.title} ({self._format_currency(book.price)}) - {book.category}\n"
        
        if remaining > 0:
            message += f"\n... và còn {remaining} sách khác."
        
        return {
            "message": message,
            "intent": "search_success",
            "data": {"books": [book.__dict__ for book in shown_books]},
            "suggestions": [f"Đặt mua {book.title}" for book in shown_books[:3]]
        }
    
    def _handle_search_by_category(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý tìm kiếm theo thể loại"""
        category = intent_result.parameters.get("category")
        
        # Nếu không có category cụ thể, chuyển sang list categories
        if not category or category.strip().lower() in {"sach", "sách", "the loai", "thể loại", "loai", "loại"}:
            return self._handle_list_categories(intent_result, session_id)
        
        books = self.db_manager.get_books_by_category(category)
        
        if not books:
            return {
                "message": f"Không tìm thấy sách nào thuộc thể loại '{category}'.",
                "intent": "search_error"
            }
        
        # Giới hạn kết quả
        max_results = 5
        shown_books = books[:max_results]
        remaining = len(books) - max_results
        
        message = f"Sách thuộc thể loại '{category}':\n\n"
        for i, book in enumerate(shown_books, 1):
            message += f"{i}. {book.title} - {book.author} ({self._format_currency(book.price)})\n"
        
        if remaining > 0:
            message += f"\n... và còn {remaining} sách khác."
        
        return {
            "message": message,
            "intent": "search_success",
            "data": {"books": [book.__dict__ for book in shown_books]},
            "suggestions": [f"Đặt mua {book.title}" for book in shown_books[:3]]
        }
    
    def _handle_search_by_price(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý tìm kiếm theo giá"""
        price_range = intent_result.parameters.get("price_range")
        
        if not price_range:
            return {
                "message": "Vui lòng chỉ định khoảng giá (ví dụ: 'giá trên 200000', 'giá dưới 150000').",
                "intent": "search_error"
            }
        
        min_price, max_price = price_range
        books = self.db_manager.get_books_by_price_range(min_price, max_price)
        
        if not books:
            if min_price and max_price:
                range_str = f"{self._format_currency(min_price)} - {self._format_currency(max_price)}"
            elif min_price:
                range_str = f"từ {self._format_currency(min_price)} trở lên"
            else:
                range_str = f"dưới {self._format_currency(max_price)}"
            
            return {
                "message": f"Không tìm thấy sách nào trong khoảng giá {range_str}.",
                "intent": "search_error"
            }
        
        # Giới hạn kết quả
        max_results = 5
        shown_books = books[:max_results]
        remaining = len(books) - max_results
        
        if min_price and max_price:
            range_str = f"{self._format_currency(min_price)} - {self._format_currency(max_price)}"
        elif min_price:
            range_str = f"từ {self._format_currency(min_price)} trở lên"
        else:
            range_str = f"dưới {self._format_currency(max_price)}"
        
        message = f"Sách có giá {range_str}:\n\n"
        for i, book in enumerate(shown_books, 1):
            message += f"{i}. {book.title} - {book.author} ({self._format_currency(book.price)})\n"
        
        if remaining > 0:
            message += f"\n... và còn {remaining} sách khác."
        
        return {
            "message": message,
            "intent": "search_success",
            "data": {"books": [book.__dict__ for book in shown_books]},
            "suggestions": [f"Đặt mua {book.title}" for book in shown_books[:3]]
        }
    
    def _handle_recommend(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý gợi ý sách"""
        books = self.db_manager.get_all_books()
        
        if not books:
            return {
                "message": "Không có sách để gợi ý.",
                "intent": "recommend_error"
            }
        
        # Chọn ngẫu nhiên 3 sách
        recommended_books = random.sample(books, min(3, len(books)))
        
        message = "📚 Gợi ý sách hay:\n\n"
        for i, book in enumerate(recommended_books, 1):
            message += f"{i}. {book.title} - {book.author}\n   Giá: {self._format_currency(book.price)} | Thể loại: {book.category}\n\n"
        
        return {
            "message": message,
            "intent": "recommend_success",
            "data": {"books": [book.__dict__ for book in recommended_books]},
            "suggestions": [f"Đặt mua {book.title}" for book in recommended_books]
        }
    
    def _handle_recommend_by_price(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý gợi ý sách theo giá"""
        price_range = intent_result.parameters.get("price_range")
        
        if not price_range:
            return {
                "message": "Vui lòng chỉ định khoảng giá (ví dụ: 'sách nào hay dưới 150000').",
                "intent": "recommend_error"
            }
        
        min_price, max_price = price_range
        books = self.db_manager.get_books_by_price_range(min_price, max_price)
        
        if not books:
            if min_price and max_price:
                range_str = f"{self._format_currency(min_price)} - {self._format_currency(max_price)}"
            elif min_price:
                range_str = f"từ {self._format_currency(min_price)} trở lên"
            else:
                range_str = f"dưới {self._format_currency(max_price)}"
            
            return {
                "message": f"Không tìm thấy sách nào trong khoảng giá {range_str}.",
                "intent": "recommend_error"
            }
        
        # Chọn ngẫu nhiên 3 sách từ danh sách đã lọc
        recommended_books = random.sample(books, min(3, len(books)))
        
        if min_price and max_price:
            range_str = f"{self._format_currency(min_price)} - {self._format_currency(max_price)}"
        elif min_price:
            range_str = f"từ {self._format_currency(min_price)} trở lên"
        else:
            range_str = f"dưới {self._format_currency(max_price)}"
        
        message = f"📚 Gợi ý sách hay trong khoảng giá {range_str}:\n\n"
        for i, book in enumerate(recommended_books, 1):
            message += f"{i}. {book.title} - {book.author}\n   Giá: {self._format_currency(book.price)} | Thể loại: {book.category}\n\n"
        
        if len(books) > 3:
            message += f"💡 Còn {len(books) - 3} cuốn sách khác trong khoảng giá này!"
        
        return {
            "message": message,
            "intent": "recommend_success",
            "data": {"books": [book.__dict__ for book in recommended_books]},
            "suggestions": [f"Đặt mua {book.title}" for book in recommended_books]
        }
    
    def _handle_list_categories(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý liệt kê thể loại"""
        categories = self.db_manager.get_all_categories()
        
        if not categories:
            return {
                "message": "Không có thể loại sách nào.",
                "intent": "list_categories_error"
            }
        
        # Giới hạn kết quả
        max_results = 10
        shown_categories = categories[:max_results]
        remaining = len(categories) - max_results
        
        message = "📂 Cửa hàng có các loại sách sau:\n\n"
        for i, category in enumerate(shown_categories, 1):
            message += f"{i}. {category}\n"
        
        if remaining > 0:
            message += f"\n... và còn {remaining} loại nữa."
        
        return {
            "message": message,
            "intent": "list_categories_success",
            "data": {"categories": shown_categories},
            "suggestions": [f"Sách về {category}" for category in shown_categories[:5]]
        }
    
    def _handle_check_stock(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý kiểm tra tồn kho"""
        book_title = intent_result.parameters.get("book_title")
        
        if not book_title:
            return {
                "message": "Vui lòng chỉ định tên sách (ví dụ: 'Gilead').",
                "intent": "check_stock_error"
            }
        
        books = self.db_manager.search_books(book_title)
        
        if not books:
            return {
                "message": f"Không tìm thấy sách '{book_title}'.",
                "intent": "check_stock_error"
            }
        
        book = books[0]
        
        if book.stock > 0:
            message = f"Sách '{book.title}' còn {book.stock} cuốn trong kho."
        else:
            message = f"Sách '{book.title}' đã hết hàng."
        
        return {
            "message": message,
            "intent": "check_stock_success",
            "data": {"book": book.__dict__},
            "suggestions": [f"Đặt mua {book.title}"] if book.stock > 0 else []
        }
    
    def _handle_greeting(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý chào hỏi với sentiment awareness"""
        # Lấy context để hiểu sở thích người dùng
        context = self.nlp_processor.get_conversation_context(session_id)
        user_preferences = context.user_preferences
        
        # Tạo lời chào cá nhân hóa
        if user_preferences.get('preferred_categories'):
            categories = ', '.join(user_preferences['preferred_categories'][:2])
            message = f"Xin chào! Tôi thấy bạn quan tâm đến sách về {categories}. Tôi có thể giúp bạn tìm kiếm sách, tra cứu thông tin và đặt hàng. Bạn cần hỗ trợ gì?"
        elif user_preferences.get('preferred_authors'):
            authors = ', '.join(user_preferences['preferred_authors'][:2])
            message = f"Xin chào! Tôi thấy bạn thích sách của {authors}. Tôi có thể giúp bạn tìm kiếm sách, tra cứu thông tin và đặt hàng. Bạn cần hỗ trợ gì?"
        else:
            greetings = [
                "Xin chào! Tôi là chatbot của cửa hàng sách. Tôi có thể giúp bạn tìm kiếm sách, tra cứu thông tin và đặt hàng. Bạn cần hỗ trợ gì?",
                "Chào bạn! Tôi có thể giúp bạn tìm sách, hỏi giá, đặt hàng hoặc gợi ý sách hay. Bạn muốn làm gì?",
                "Hello! Tôi là trợ lý ảo của cửa hàng sách. Tôi có thể hỗ trợ bạn tra cứu thông tin sách và đặt hàng. Có gì tôi có thể giúp bạn?"
            ]
            message = random.choice(greetings)
        
        # Lấy smart suggestions
        smart_suggestions = self.nlp_processor.get_smart_suggestions(session_id, IntentType.GREETING)
        
        return {
            "message": message,
            "intent": "greeting_success",
            "suggestions": smart_suggestions
        }
    
    def _handle_goodbye(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý tạm biệt"""
        goodbyes = [
            "Tạm biệt! Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi. Hẹn gặp lại!",
            "Chào tạm biệt! Nếu cần hỗ trợ gì thêm, bạn có thể quay lại bất cứ lúc nào.",
            "Goodbye! Cảm ơn bạn đã ghé thăm cửa hàng sách của chúng tôi."
        ]
        
        message = random.choice(goodbyes)
        
        return {
            "message": message,
            "intent": "goodbye_success"
        }
    
    def _handle_help(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý yêu cầu trợ giúp"""
        message = """🤖 Tôi có thể giúp bạn:

📚 **Tìm kiếm sách:**
• "Tìm sách Gilead"
• "Sách của Sidney Sheldon"
• "Sách về Fiction"

💰 **Tra cứu giá:**
• "Giá sách Gilead"
• "Sách dưới 100000"
• "Giá từ 50000 đến 150000"

🛒 **Đặt hàng:**
• "Đặt mua Gilead"
• "Mua sách Rage of angels"

💡 **Gợi ý:**
• "Gợi ý sách hay"
• "Sách nào hay dưới 150000"

📂 **Thể loại:**
• "Cửa hàng có những loại sách gì?"

Bạn muốn thử tính năng nào?"""
        
        return {
            "message": message,
            "intent": "help_success",
            "suggestions": [
                "Gợi ý sách hay",
                "Cửa hàng có những loại sách gì?",
                "Sách về Fiction",
                "Giá dưới 100000"
            ]
        }
    
    def _handle_unknown_intent(self, intent_result: IntentResult, session_id: str) -> Dict[str, Any]:
        """Xử lý intent không xác định với sentiment awareness"""
        # Kiểm tra sentiment để điều chỉnh phản hồi
        sentiment = intent_result.sentiment
        
        if sentiment == SentimentType.FRUSTRATED:
            message = "Tôi hiểu bạn đang gặp khó khăn. Đừng lo, tôi sẽ giúp bạn! Bạn có thể thử:\n\n• 'Gợi ý sách hay'\n• 'Giá sách Gilead'\n• 'Đặt mua Gilead'\n• 'Cửa hàng có những loại sách gì?'\n\nHoặc gõ 'help' để xem hướng dẫn chi tiết."
        elif sentiment == SentimentType.NEGATIVE:
            message = "Xin lỗi vì sự bất tiện. Tôi sẽ cố gắng hiểu rõ hơn yêu cầu của bạn. Bạn có thể thử:\n\n• 'Gợi ý sách hay'\n• 'Giá sách Gilead'\n• 'Đặt mua Gilead'\n• 'Cửa hàng có những loại sách gì?'\n\nHoặc gõ 'help' để xem hướng dẫn chi tiết."
        else:
            message = "Xin lỗi, tôi không hiểu yêu cầu của bạn. Bạn có thể thử:\n\n• 'Gợi ý sách hay'\n• 'Giá sách Gilead'\n• 'Đặt mua Gilead'\n• 'Cửa hàng có những loại sách gì?'\n\nHoặc gõ 'help' để xem hướng dẫn chi tiết."
        
        # Lấy smart suggestions
        smart_suggestions = self.nlp_processor.get_smart_suggestions(session_id, IntentType.UNKNOWN)
        
        return {
            "message": message,
            "intent": "unknown",
            "suggestions": smart_suggestions
        }
    
    def _format_currency(self, amount: int) -> str:
        """Định dạng tiền tệ"""
        return f"{amount:,}".replace(",", ".") + " VND"
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Lấy thông tin session"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return {"error": "Session không tồn tại"}
        
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "order_state": session.order_state.value,
            "order_data": session.order_data.__dict__ if session.order_data else None,
            "conversation_count": len(session.conversation_history),
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê hệ thống"""
        db_stats = self.db_manager.get_statistics()
        session_stats = self.session_manager.get_session_statistics()
        
        return {
            "database": db_stats,
            "sessions": session_stats,
            "timestamp": datetime.now().isoformat()
        }

# Singleton instance
optimized_chatbot = OptimizedChatbot()
