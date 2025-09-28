"""
Simple Streamlit App - Giao diện đơn giản cho BookStore Chatbot
"""
import streamlit as st
import time
from datetime import datetime
from chatbot import OptimizedChatbot

# Tạo instance chatbot
chatbot = OptimizedChatbot()

# Cấu hình trang
st.set_page_config(
    page_title="BookStore Chatbot",
    page_icon="📚",
    layout="centered"
)

# CSS đơn giản
st.markdown("""
<style>
    /* Ẩn các element không cần thiết */
    .css-1d391kg {display: none;}
    .css-1rs6os {display: none;}
    .css-1v0mbdj {display: none;}
    
    /* Container chính */
    .main-container {
        max-width: 600px;
        margin: 0 auto;
        padding: 0.5rem;
    }
    
    /* Chat container */
    .chat-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 0.5rem;
        margin: 0.5rem 0;
        min-height: 350px;
        max-height: 450px;
        overflow-y: auto;
        background-color: #fafafa;
    }
    
    /* Messages */
    .user-msg {
        background-color: #007bff;
        color: white;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border-radius: 18px 18px 4px 18px;
        max-width: 80%;
        margin-left: auto;
        text-align: right;
    }
    
    .bot-msg {
        background-color: white;
        color: #333;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border-radius: 18px 18px 18px 4px;
        max-width: 80%;
        border: 1px solid #ddd;
    }
    
    /* Input area */
    .input-area {
        border-top: 1px solid #ddd;
        padding-top: 0.5rem;
        margin-top: 0.5rem;
    }
    
    /* Quick actions */
    .quick-actions {
        display: flex;
        gap: 0.5rem;
        margin: 0.5rem 0;
        flex-wrap: wrap;
    }
    
    .quick-btn {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 20px;
        padding: 0.3rem 0.8rem;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .quick-btn:hover {
        background-color: #e9ecef;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session():
    """Khởi tạo session state"""
    if "session_id" not in st.session_state:
        from session_manager import session_manager
        st.session_state.session_id = session_manager.create_session()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "should_scroll" not in st.session_state:
        st.session_state.should_scroll = False

def process_user_input(user_input):
    """Xử lý input từ user"""
    try:
        # Thêm tin nhắn user
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Xử lý với chatbot
        result = chatbot.process_message(user_input, st.session_state.session_id)
        
        # Thêm tin nhắn bot
        st.session_state.messages.append({
            "role": "assistant",
            "content": result.get("message", "Xin lỗi, tôi không hiểu câu hỏi của bạn."),
            "timestamp": datetime.now().isoformat(),
            "suggestions": result.get("suggestions", [])
        })
        
        st.session_state.should_scroll = True
        
    except Exception as e:
        st.error(f"Lỗi: {str(e)}")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.",
            "timestamp": datetime.now().isoformat()
        })

def display_messages():
    """Hiển thị tin nhắn"""
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    if not st.session_state.messages:
        # Header và tin nhắn chào mừng gộp chung
        st.markdown("""
        <div style="text-align: center; padding: 1rem; color: #333;">
            <h1>BookStore Chatbot</h1>
            <p style="color: #666; margin: 0.5rem 0;">Hỏi tôi về sách, giá cả, thể loại và đặt hàng</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Gợi ý nhanh
        st.markdown('<div class="quick-actions">', unsafe_allow_html=True)
        quick_actions = [
            "Thể loại sách",
            "Gợi ý sách hay", 
            "Sách về Fiction",
            "Giá dưới 100000"
        ]
        
        cols = st.columns(len(quick_actions))
        for i, action in enumerate(quick_actions):
            with cols[i]:
                if st.button(action, key=f"quick_{i}", use_container_width=True):
                    process_user_input(action)
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Hiển thị tin nhắn
        for msg_idx, message in enumerate(st.session_state.messages):
            if message["role"] == "user":
                st.markdown(f'<div class="user-msg">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bot-msg">{message["content"]}</div>', unsafe_allow_html=True)
                
                # Hiển thị suggestions nếu có
                if message.get("suggestions"):
                    st.markdown("**Gợi ý:**")
                    cols = st.columns(len(message["suggestions"]))
                    for i, suggestion in enumerate(message["suggestions"]):
                        with cols[i]:
                            if st.button(suggestion, key=f"suggestion_{msg_idx}_{i}", use_container_width=True):
                                process_user_input(suggestion)
                                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Auto scroll JavaScript
    if st.session_state.should_scroll:
        st.markdown("""
        <script>
            setTimeout(function() {
                var chatContainer = document.querySelector('.chat-container');
                if (chatContainer) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }, 100);
        </script>
        """, unsafe_allow_html=True)
        st.session_state.should_scroll = False

def display_input():
    """Hiển thị input area"""
    st.markdown('<div class="input-area">', unsafe_allow_html=True)
    
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            user_input = st.text_input("Nhập câu hỏi của bạn:", placeholder="Ví dụ: Tìm sách về Fiction", key="user_input")
        with col2:
            submitted = st.form_submit_button("Gửi", use_container_width=True)
    
    # Nút xóa chat
    if st.session_state.messages:
        if st.button("Xóa chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.should_scroll = False
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Xử lý khi submit
    if submitted and user_input:
        process_user_input(user_input)
        st.rerun()

def main():
    """Hàm chính"""
    initialize_session()
    
    # Container chính
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Hiển thị tin nhắn (đã tích hợp header)
    display_messages()
    
    # Input area
    display_input()
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Lỗi ứng dụng: {str(e)}")
        st.exception(e)
