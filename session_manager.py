"""
Session Manager - Quản lý session và trạng thái hội thoại tối ưu
"""
import json
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class OrderState(Enum):
    """Trạng thái đặt hàng"""
    NONE = "none"
    WAITING_QUANTITY = "waiting_quantity"
    WAITING_ADDRESS_PHONE = "waiting_address_phone"
    CONFIRMING_ORDER = "confirming_order"
    PROCESSING_ORDER = "processing_order"
    ORDER_COMPLETED = "order_completed"
    ORDER_CANCELLED = "order_cancelled"

class SessionType(Enum):
    """Loại session"""
    CHAT = "chat"
    ORDER = "order"
    SEARCH = "search"

@dataclass
class OrderData:
    """Dữ liệu đơn hàng"""
    book_id: str
    book_title: str
    price: int
    quantity: int
    customer_name: str
    phone: str
    address: str
    total_price: int
    created_at: str
    updated_at: str

@dataclass
class SessionData:
    """Dữ liệu session"""
    session_id: str
    user_id: str
    session_type: SessionType
    order_state: OrderState
    order_data: Optional[OrderData]
    conversation_history: List[Dict[str, Any]]
    context: Dict[str, Any]
    created_at: str
    updated_at: str
    expires_at: str

class SessionManager:
    """Quản lý session và trạng thái hội thoại"""
    
    def __init__(self, session_timeout: int = 3600):  # 1 giờ
        self.sessions: Dict[str, SessionData] = {}
        self.session_timeout = session_timeout
        self.cleanup_interval = 300  # 5 phút
        self.last_cleanup = datetime.now()
    
    def create_session(self, user_id: str = None, session_type: SessionType = SessionType.CHAT) -> str:
        """Tạo session mới"""
        session_id = str(uuid.uuid4())
        if not user_id:
            user_id = f"user_{session_id[:8]}"
        
        session_data = SessionData(
            session_id=session_id,
            user_id=user_id,
            session_type=session_type,
            order_state=OrderState.NONE,
            order_data=None,
            conversation_history=[],
            context={},
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(seconds=self.session_timeout)).isoformat()
        )
        
        self.sessions[session_id] = session_data
        logger.info(f"Created new session: {session_id} for user: {user_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Lấy thông tin session"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Kiểm tra session có hết hạn không
        if datetime.now() > datetime.fromisoformat(session.expires_at):
            self.delete_session(session_id)
            return None
        
        # Cập nhật thời gian truy cập
        session.updated_at = datetime.now().isoformat()
        return session
    
    def update_session(self, session_id: str, **kwargs) -> bool:
        """Cập nhật thông tin session"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Cập nhật các trường được chỉ định
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.updated_at = datetime.now().isoformat()
        return True
    
    def add_message_to_history(self, session_id: str, role: str, content: str, metadata: Dict = None) -> bool:
        """Thêm tin nhắn vào lịch sử hội thoại"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        session.conversation_history.append(message)
        
        # Giới hạn lịch sử hội thoại (giữ lại 50 tin nhắn gần nhất)
        if len(session.conversation_history) > 50:
            session.conversation_history = session.conversation_history[-50:]
        
        session.updated_at = datetime.now().isoformat()
        return True
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Lấy lịch sử hội thoại"""
        session = self.get_session(session_id)
        if not session:
            return []
        
        return session.conversation_history[-limit:] if limit > 0 else session.conversation_history
    
    def set_order_state(self, session_id: str, state: OrderState) -> bool:
        """Thiết lập trạng thái đặt hàng"""
        return self.update_session(session_id, order_state=state)
    
    def get_order_state(self, session_id: str) -> OrderState:
        """Lấy trạng thái đặt hàng hiện tại"""
        session = self.get_session(session_id)
        return session.order_state if session else OrderState.NONE
    
    def set_order_data(self, session_id: str, order_data: OrderData) -> bool:
        """Thiết lập dữ liệu đơn hàng"""
        return self.update_session(session_id, order_data=order_data)
    
    def get_order_data(self, session_id: str) -> Optional[OrderData]:
        """Lấy dữ liệu đơn hàng hiện tại"""
        session = self.get_session(session_id)
        return session.order_data if session else None
    
    def update_order_data(self, session_id: str, **kwargs) -> bool:
        """Cập nhật dữ liệu đơn hàng"""
        session = self.get_session(session_id)
        if not session or not session.order_data:
            return False
        
        # Cập nhật các trường được chỉ định
        for key, value in kwargs.items():
            if hasattr(session.order_data, key):
                setattr(session.order_data, key, value)
        
        session.order_data.updated_at = datetime.now().isoformat()
        session.updated_at = datetime.now().isoformat()
        return True
    
    def clear_order_data(self, session_id: str) -> bool:
        """Xóa dữ liệu đơn hàng"""
        return self.update_session(session_id, order_data=None, order_state=OrderState.NONE)
    
    def set_context(self, session_id: str, key: str, value: Any) -> bool:
        """Thiết lập context"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.context[key] = value
        session.updated_at = datetime.now().isoformat()
        return True
    
    def get_context(self, session_id: str, key: str, default: Any = None) -> Any:
        """Lấy context"""
        session = self.get_session(session_id)
        if not session:
            return default
        
        return session.context.get(key, default)
    
    def clear_context(self, session_id: str) -> bool:
        """Xóa context"""
        return self.update_session(session_id, context={})
    
    def delete_session(self, session_id: str) -> bool:
        """Xóa session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Dọn dẹp các session đã hết hạn"""
        current_time = datetime.now()
        
        # Chỉ cleanup mỗi 5 phút
        if (current_time - self.last_cleanup).seconds < self.cleanup_interval:
            return
        
        expired_sessions = []
        for session_id, session in self.sessions.items():
            if current_time > datetime.fromisoformat(session.expires_at):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.delete_session(session_id)
        
        self.last_cleanup = current_time
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê session"""
        self.cleanup_expired_sessions()
        
        total_sessions = len(self.sessions)
        active_sessions = 0
        order_sessions = 0
        
        for session in self.sessions.values():
            if datetime.now() <= datetime.fromisoformat(session.expires_at):
                active_sessions += 1
                if session.order_state != OrderState.NONE:
                    order_sessions += 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "order_sessions": order_sessions,
            "expired_sessions": total_sessions - active_sessions
        }
    
    def export_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Xuất dữ liệu session"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return asdict(session)
    
    def import_session_data(self, session_data: Dict[str, Any]) -> str:
        """Nhập dữ liệu session"""
        session_id = session_data.get("session_id", str(uuid.uuid4()))
        
        # Chuyển đổi dữ liệu
        session = SessionData(
            session_id=session_id,
            user_id=session_data.get("user_id", f"user_{session_id[:8]}"),
            session_type=SessionType(session_data.get("session_type", "chat")),
            order_state=OrderState(session_data.get("order_state", "none")),
            order_data=OrderData(**session_data["order_data"]) if session_data.get("order_data") else None,
            conversation_history=session_data.get("conversation_history", []),
            context=session_data.get("context", {}),
            created_at=session_data.get("created_at", datetime.now().isoformat()),
            updated_at=session_data.get("updated_at", datetime.now().isoformat()),
            expires_at=session_data.get("expires_at", (datetime.now() + timedelta(seconds=self.session_timeout)).isoformat())
        )
        
        self.sessions[session_id] = session
        return session_id

class OrderFlowManager:
    """Quản lý quy trình đặt hàng"""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
    
    def start_order(self, session_id: str, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """Bắt đầu quy trình đặt hàng"""
        # Tạo dữ liệu đơn hàng
        order_data = OrderData(
            book_id=book_data.get("book_id", ""),
            book_title=book_data.get("title", ""),
            price=book_data.get("price", 0),
            quantity=1,  # Mặc định
            customer_name="Khách hàng",
            phone="",
            address="",
            total_price=book_data.get("price", 0),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Cập nhật session
        self.session_manager.set_order_data(session_id, order_data)
        self.session_manager.set_order_state(session_id, OrderState.WAITING_QUANTITY)
        
        return {
            "status": "success",
            "message": f"Sách '{book_data.get('title', '')}' giá {self._format_currency(book_data.get('price', 0))}. Vui lòng nhập số lượng.",
            "order_data": asdict(order_data)
        }
    
    def process_quantity(self, session_id: str, quantity: int) -> Dict[str, Any]:
        """Xử lý số lượng đặt hàng"""
        if not self.session_manager.update_order_data(session_id, quantity=quantity):
            return {"status": "error", "message": "Không thể cập nhật số lượng."}
        
        # Tính lại tổng tiền
        order_data = self.session_manager.get_order_data(session_id)
        if order_data:
            total_price = order_data.price * quantity
            self.session_manager.update_order_data(session_id, total_price=total_price)
            
            # Chuyển sang bước tiếp theo
            self.session_manager.set_order_state(session_id, OrderState.WAITING_ADDRESS_PHONE)
            
            return {
                "status": "success",
                "message": f"Số lượng: {quantity}. Tổng tiền: {self._format_currency(total_price)}. Vui lòng nhập địa chỉ giao hàng và số điện thoại (ví dụ: '123 Hà Nội, 0987654321').",
                "order_data": asdict(order_data)
            }
        
        return {"status": "error", "message": "Không tìm thấy thông tin đơn hàng."}
    
    def process_address_phone(self, session_id: str, address: str, phone: str) -> Dict[str, Any]:
        """Xử lý địa chỉ và số điện thoại"""
        if not self.session_manager.update_order_data(session_id, address=address, phone=phone):
            return {"status": "error", "message": "Không thể cập nhật thông tin giao hàng."}
        
        # Chuyển sang bước xác nhận
        self.session_manager.set_order_state(session_id, OrderState.CONFIRMING_ORDER)
        
        order_data = self.session_manager.get_order_data(session_id)
        if order_data:
            return {
                "status": "success",
                "message": f"Xác nhận đặt: '{order_data.book_title}', SL: {order_data.quantity}, Địa chỉ: {order_data.address}, SĐT: {order_data.phone}. Tổng: {self._format_currency(order_data.total_price)}. Trả lời 'có' để xác nhận hoặc 'không' để hủy.",
                "order_data": asdict(order_data)
            }
        
        return {"status": "error", "message": "Không tìm thấy thông tin đơn hàng."}
    
    def confirm_order(self, session_id: str, confirmed: bool) -> Dict[str, Any]:
        """Xác nhận hoặc hủy đơn hàng"""
        if confirmed:
            self.session_manager.set_order_state(session_id, OrderState.PROCESSING_ORDER)
            return {
                "status": "success",
                "message": "Đơn hàng đã được xác nhận. Đang xử lý...",
                "action": "process_order"
            }
        else:
            self.session_manager.clear_order_data(session_id)
            return {
                "status": "success",
                "message": "Đã hủy đơn hàng.",
                "action": "order_cancelled"
            }
    
    def complete_order(self, session_id: str, order_result: Dict[str, Any]) -> Dict[str, Any]:
        """Hoàn tất đơn hàng"""
        if order_result.get("success"):
            self.session_manager.set_order_state(session_id, OrderState.ORDER_COMPLETED)
            return {
                "status": "success",
                "message": order_result.get("message", "Đơn hàng đã được tạo thành công."),
                "action": "order_completed"
            }
        else:
            self.session_manager.set_order_state(session_id, OrderState.ORDER_CANCELLED)
            return {
                "status": "error",
                "message": order_result.get("message", "Có lỗi xảy ra khi tạo đơn hàng."),
                "action": "order_failed"
            }
    
    def get_order_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Lấy tóm tắt đơn hàng"""
        order_data = self.session_manager.get_order_data(session_id)
        if not order_data:
            return None
        
        return {
            "book_title": order_data.book_title,
            "quantity": order_data.quantity,
            "price": order_data.price,
            "total_price": order_data.total_price,
            "address": order_data.address,
            "phone": order_data.phone,
            "status": self.session_manager.get_order_state(session_id).value
        }
    
    def _format_currency(self, amount: int) -> str:
        """Định dạng tiền tệ"""
        return f"{amount:,}".replace(",", ".") + " VND"

# Singleton instances
session_manager = SessionManager()
order_flow_manager = OrderFlowManager(session_manager)

