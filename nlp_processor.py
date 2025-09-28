"""
NLP Processor - Xử lý ngôn ngữ tự nhiên tối ưu cho BookStore Chatbot
"""
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from difflib import SequenceMatcher
import unicodedata
from fuzzywuzzy import fuzz, process
import numpy as np
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """Các loại intent được hỗ trợ"""
    ORDER = "order"
    QUERY = "query"
    SEARCH_BY_TITLE = "search_by_title"
    SEARCH_BY_AUTHOR = "search_by_author"
    SEARCH_BY_CATEGORY = "search_by_category"
    SEARCH_BY_PRICE = "search_by_price"
    RECOMMEND = "recommend"
    RECOMMEND_BY_PRICE = "recommend_by_price"
    RECOMMEND_BEST = "recommend_best"
    LIST_CATEGORIES = "list_categories"
    CHECK_STOCK = "check_stock"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    HELP = "help"
    COMPARISON = "comparison"
    REVIEW = "review"
    UNKNOWN = "unknown"

class SentimentType(Enum):
    """Các loại cảm xúc"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    EXCITED = "excited"

@dataclass
class ExtractedEntity:
    """Cấu trúc entity được trích xuất"""
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    entity_type: str

@dataclass
class IntentResult:
    """Kết quả phân tích intent"""
    intent: IntentType
    confidence: float
    entities: List[ExtractedEntity]
    parameters: Dict[str, Any]
    original_text: str
    sentiment: Optional[SentimentType] = None
    context: Optional[Dict[str, Any]] = None

@dataclass
class ConversationContext:
    """Context của cuộc hội thoại"""
    session_id: str
    conversation_history: Optional[deque] = None
    user_preferences: Optional[Dict[str, Any]] = None
    current_topic: Optional[str] = None
    last_intent: Optional[IntentType] = None
    user_sentiment_history: Optional[List[SentimentType]] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = deque(maxlen=10)  # Giữ 10 tin nhắn gần nhất
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.user_sentiment_history is None:
            self.user_sentiment_history = []

class VietnameseTextProcessor:
    """Xử lý văn bản tiếng Việt"""
    
    # Từ khóa tiếng Việt thường dùng
    VIETNAMESE_KEYWORDS = {
        'order': ['đặt', 'mua', 'order', 'mua sách', 'đặt sách', 'đặt mua', 'mua cuốn'],
        'query': ['giá', 'bao nhiêu', 'thông tin', 'tra cứu', 'hỏi', 'tìm hiểu'],
        'search': ['tìm', 'tìm kiếm', 'search', 'có sách', 'có cuốn'],
        'author': ['tác giả', 'sách của', 'viết bởi', 'tác phẩm của'],
        'category': ['thể loại', 'loại sách', 'sách về', 'thuộc loại', 'phân loại'],
        'price': ['giá', 'tiền', 'cost', 'price', 'bao nhiêu tiền'],
        'recommend': ['gợi ý', 'hay', 'tốt', 'đáng đọc', 'nên đọc', 'khuyên'],
        'stock': ['tồn kho', 'còn hàng', 'có sẵn', 'số lượng', 'còn bao nhiêu'],
        'greeting': ['xin chào', 'chào', 'hello', 'hi', 'chào bạn'],
        'goodbye': ['tạm biệt', 'bye', 'goodbye', 'hẹn gặp lại'],
        'help': ['giúp', 'help', 'hướng dẫn', 'làm sao', 'như thế nào']
    }
    
    # Từ viết tắt và từ đồng nghĩa
    SYNONYMS = {
        'sách': ['cuốn', 'quyển', 'tập', 'book'],
        'giá': ['tiền', 'cost', 'price'],
        'tác giả': ['writer', 'author'],
        'thể loại': ['category', 'genre', 'loại'],
        'đặt': ['mua', 'order', 'purchase'],
        'hay': ['tốt', 'đáng đọc', 'interesting', 'good']
    }
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Chuẩn hóa văn bản tiếng Việt"""
        if not text:
            return ""
        
        # Chuyển về chữ thường
        text = text.lower().strip()
        
        # Loại bỏ dấu câu thừa (giữ lại dấu tiếng Việt)
        text = re.sub(r'[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', ' ', text)
        
        # Chuẩn hóa khoảng trắng
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    @staticmethod
    def expand_synonyms(text: str) -> str:
        """Mở rộng từ đồng nghĩa"""
        for main_word, synonyms in VietnameseTextProcessor.SYNONYMS.items():
            for synonym in synonyms:
                text = re.sub(rf'\b{synonym}\b', main_word, text)
        return text
    
    @staticmethod
    def remove_stopwords(text: str) -> str:
        """Loại bỏ từ dừng"""
        stopwords = {
            'của', 'và', 'hoặc', 'nhưng', 'mà', 'để', 'với', 'từ', 'đến', 'trong',
            'ngoài', 'trên', 'dưới', 'giữa', 'bên', 'cạnh', 'gần', 'xa', 'này',
            'đó', 'kia', 'đây', 'đó', 'nào', 'gì', 'sao', 'thế', 'vậy', 'à',
            'ạ', 'nhé', 'nhỉ', 'đấy', 'đó', 'thôi', 'thế', 'vậy', 'mà', 'thì'
        }
        
        words = text.split()
        filtered_words = [word for word in words if word not in stopwords]
        return ' '.join(filtered_words)

class SentimentAnalyzer:
    """Phân tích cảm xúc từ văn bản tiếng Việt"""
    
    # Từ khóa cảm xúc tích cực
    POSITIVE_KEYWORDS = {
        'tốt', 'hay', 'tuyệt', 'xuất sắc', 'đẹp', 'thích', 'yêu', 'hài lòng',
        'vui', 'hạnh phúc', 'thú vị', 'hấp dẫn', 'cuốn hút', 'ấn tượng',
        'cảm ơn', 'thanks', 'thank you', 'cảm ơn bạn', 'tuyệt vời',
        'hoàn hảo', 'chất lượng', 'đáng giá', 'nên mua', 'khuyên'
    }
    
    # Từ khóa cảm xúc tiêu cực
    NEGATIVE_KEYWORDS = {
        'tệ', 'xấu', 'không thích', 'ghét', 'chán', 'nhàm chán', 'thất vọng',
        'buồn', 'tức giận', 'khó chịu', 'phiền', 'không hài lòng',
        'đắt', 'mắc', 'không đáng', 'lừa đảo', 'giả', 'kém chất lượng',
        'hết hàng', 'không có', 'thất bại', 'lỗi', 'sai'
    }
    
    # Từ khóa thể hiện sự thất vọng
    FRUSTRATED_KEYWORDS = {
        'tại sao', 'sao lại', 'không hiểu', 'khó hiểu', 'phức tạp',
        'rối rắm', 'không biết', 'làm sao', 'như thế nào', 'help',
        'giúp', 'hướng dẫn', 'không tìm thấy', 'không có'
    }
    
    # Từ khóa thể hiện sự phấn khích
    EXCITED_KEYWORDS = {
        'wow', 'tuyệt quá', 'amazing', 'incredible', 'fantastic',
        'tuyệt vời', 'quá hay', 'quá tốt', 'thích quá', 'mê quá',
        'đặt ngay', 'mua ngay', 'cần ngay', 'gấp', 'urgent'
    }
    
    @classmethod
    def analyze_sentiment(cls, text: str) -> SentimentType:
        """Phân tích cảm xúc từ văn bản"""
        if not text:
            return SentimentType.NEUTRAL
        
        text_lower = text.lower()
        words = set(text_lower.split())
        
        # Đếm từ khóa cảm xúc
        positive_count = len(words.intersection(cls.POSITIVE_KEYWORDS))
        negative_count = len(words.intersection(cls.NEGATIVE_KEYWORDS))
        frustrated_count = len(words.intersection(cls.FRUSTRATED_KEYWORDS))
        excited_count = len(words.intersection(cls.EXCITED_KEYWORDS))
        
        # Xác định cảm xúc dựa trên số lượng từ khóa
        if excited_count > 0 and excited_count >= positive_count:
            return SentimentType.EXCITED
        elif frustrated_count > 0 and frustrated_count >= negative_count:
            return SentimentType.FRUSTRATED
        elif positive_count > negative_count:
            return SentimentType.POSITIVE
        elif negative_count > positive_count:
            return SentimentType.NEGATIVE
        else:
            return SentimentType.NEUTRAL

class ContextManager:
    """Quản lý context của cuộc hội thoại"""
    
    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}
    
    def get_context(self, session_id: str) -> ConversationContext:
        """Lấy context của session"""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext(
                session_id=session_id,
                conversation_history=deque(maxlen=10),
                user_preferences={},
                current_topic=None,
                last_intent=None,
                user_sentiment_history=[]
            )
        return self.contexts[session_id]
    
    def update_context(self, session_id: str, user_input: str, intent_result: IntentResult):
        """Cập nhật context sau khi xử lý tin nhắn"""
        context = self.get_context(session_id)
        
        # Thêm vào lịch sử hội thoại
        context.conversation_history.append({
            'user_input': user_input,
            'intent': intent_result.intent,
            'sentiment': intent_result.sentiment,
            'timestamp': datetime.now().isoformat()
        })
        
        # Cập nhật intent cuối
        context.last_intent = intent_result.intent
        
        # Cập nhật lịch sử cảm xúc
        if intent_result.sentiment:
            context.user_sentiment_history.append(intent_result.sentiment)
            # Giữ tối đa 5 cảm xúc gần nhất
            if len(context.user_sentiment_history) > 5:
                context.user_sentiment_history = context.user_sentiment_history[-5:]
        
        # Cập nhật topic hiện tại
        if intent_result.intent in [IntentType.SEARCH_BY_CATEGORY, IntentType.SEARCH_BY_AUTHOR]:
            context.current_topic = intent_result.parameters.get('category') or intent_result.parameters.get('author')
        
        # Cập nhật preferences
        self._update_user_preferences(context, intent_result)
    
    def _update_user_preferences(self, context: ConversationContext, intent_result: IntentResult):
        """Cập nhật sở thích người dùng"""
        if intent_result.intent == IntentType.SEARCH_BY_CATEGORY:
            category = intent_result.parameters.get('category')
            if category:
                context.user_preferences['preferred_categories'] = context.user_preferences.get('preferred_categories', [])
                if category not in context.user_preferences['preferred_categories']:
                    context.user_preferences['preferred_categories'].append(category)
        
        elif intent_result.intent == IntentType.SEARCH_BY_AUTHOR:
            author = intent_result.parameters.get('author')
            if author:
                context.user_preferences['preferred_authors'] = context.user_preferences.get('preferred_authors', [])
                if author not in context.user_preferences['preferred_authors']:
                    context.user_preferences['preferred_authors'].append(author)
        
        elif intent_result.intent == IntentType.SEARCH_BY_PRICE:
            price_range = intent_result.parameters.get('price_range')
            if price_range:
                context.user_preferences['preferred_price_range'] = price_range
    
    def get_smart_suggestions(self, session_id: str, current_intent: IntentType) -> List[str]:
        """Tạo gợi ý thông minh dựa trên context"""
        context = self.get_context(session_id)
        suggestions = []
        
        # Gợi ý dựa trên sở thích
        if context.user_preferences.get('preferred_categories'):
            for category in context.user_preferences['preferred_categories'][:2]:
                suggestions.append(f"Sách về {category}")
        
        if context.user_preferences.get('preferred_authors'):
            for author in context.user_preferences['preferred_authors'][:2]:
                suggestions.append(f"Sách của {author}")
        
        # Gợi ý dựa trên intent hiện tại
        if current_intent == IntentType.SEARCH_BY_CATEGORY:
            suggestions.extend(["Gợi ý sách hay", "Giá dưới 100000"])
        elif current_intent == IntentType.SEARCH_BY_AUTHOR:
            suggestions.extend(["Thể loại Fiction", "Sách bán chạy"])
        elif current_intent == IntentType.QUERY:
            suggestions.extend(["Đặt mua sách này", "Sách tương tự"])
        
        # Gợi ý dựa trên cảm xúc
        if context.user_sentiment_history:
            last_sentiment = context.user_sentiment_history[-1]
            if last_sentiment == SentimentType.FRUSTRATED:
                suggestions.extend(["Hướng dẫn sử dụng", "Liên hệ hỗ trợ"])
            elif last_sentiment == SentimentType.EXCITED:
                suggestions.extend(["Đặt mua ngay", "Sách tương tự"])
        
        return suggestions[:5]  # Giới hạn 5 gợi ý

class IntentClassifier:
    """Phân loại intent từ văn bản đầu vào"""
    
    def __init__(self):
        self.text_processor = VietnameseTextProcessor()
        self.intent_patterns = self._build_intent_patterns()
    
    def _build_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """Xây dựng các pattern cho từng intent"""
        return {
            IntentType.ORDER: [
                r'\b(đặt|mua|order)\s+(sách|cuốn|quyển)',
                r'\b(mua|đặt)\s+\w+',
                r'\bđặt\s+mua',
                r'\border\s+\w+',
                r'\bmua\s+\w+'
            ],
            IntentType.QUERY: [
                r'\b(giá|bao nhiêu|thông tin|tra cứu)\s+(của|về)?\s*\w+',
                r'\b(giá|bao nhiêu)\s+\w+',
                r'\bthông tin\s+(về|của)\s+\w+',
                r'\btra cứu\s+\w+',
                r'\b\w+\s+(có|tồn tại|hiện có)\s+(bao nhiêu|giá|thông tin)',
                r'\b\w+\s+(bao nhiêu|giá|thông tin)',
                r'\b(có bao nhiêu|giá bao nhiêu|thông tin gì)\s+(về|của)?\s*\w+'
            ],
            IntentType.SEARCH_BY_TITLE: [
                r'\b(tìm|tìm kiếm|có)\s+(sách|cuốn)\s+\w+',
                r'\b\w+\s+(có|tồn tại|hiện có)',
                r'\b(sách|cuốn)\s+\w+'
            ],
            IntentType.SEARCH_BY_AUTHOR: [
                r'\b(tác giả|sách của|viết bởi)\s+[\w\s]+',
                r'\b[\w\s]+\s+(viết|tác giả)',
                r'\bsách\s+(của|bởi)\s+[\w\s]+',
                r'\bsách\s+(?!về\s)(?!hay\b)(?!tốt\b)(?!đáng đọc\b)[\w\s]+'  # Pattern cho "Sách Sidney Sheldon" nhưng không bắt "sách về", "sách hay", etc.
            ],
            IntentType.SEARCH_BY_CATEGORY: [
                r'\b(thể loại|loại sách|sách về)\s+[\w\s]+',
                r'\b\w+\s+(thể loại|loại)',
                r'\bsách\s+(về|thuộc loại)\s+[\w\s]+'
            ],
            IntentType.SEARCH_BY_PRICE: [
                r'\b(giá|sách)\s+(dưới|từ|trên|cao hơn|thấp hơn)\s*\d+',
                r'\b(dưới|từ|trên)\s*\d+\s*(vnd|đồng|tiền)?',
                r'\bgiá\s+từ\s*\d+\s*đến\s*\d+',
                r'\btừ\s*\d+\s*đến\s*\d+'
            ],
            IntentType.RECOMMEND: [
                r'\b(gợi ý|hay|tốt|đáng đọc|nên đọc)',
                r'\b(sách|cuốn)\s+(hay|tốt|đáng đọc)',
                r'\bgợi ý\s+(sách|cuốn)',
                r'\b(hay nhất|bán chạy)'
            ],
            IntentType.RECOMMEND_BY_PRICE: [
                r'\b(sách|cuốn)\s+(hay|tốt|đáng đọc)\s+(dưới|từ|trên)\s*\d+',
                r'\b(hay|tốt|đáng đọc)\s+(dưới|từ|trên)\s*\d+',
                r'\bgợi ý\s+(sách|cuốn)\s+(dưới|từ|trên)\s*\d+'
            ],
            IntentType.LIST_CATEGORIES: [
                r'\b(cửa hàng|shop)\s+(có|những)\s+(loại sách|thể loại)',
                r'\b(danh sách|có những)\s+(loại sách|thể loại)',
                r'\b(loại sách|thể loại)\s+(gì|nào)'
            ],
            IntentType.CHECK_STOCK: [
                r'\b(tồn kho|còn hàng|có sẵn)\s+(của|về)?\s*\w+',
                r'\b\w+\s+(còn|có)\s+(bao nhiêu|mấy)',
                r'\b(tồn kho|còn hàng)\s+\w+'
            ],
            IntentType.GREETING: [
                r'\b(xin chào|chào|hello|hi)\b',
                r'\bchào\s+(bạn|anh|chị|em)',
                r'\bhello\s+\w+'
            ],
            IntentType.GOODBYE: [
                r'\b(tạm biệt|bye|goodbye)\b',
                r'\bhẹn\s+gặp\s+lại',
                r'\bbye\s+\w+'
            ],
            IntentType.HELP: [
                r'\b(giúp|help|hướng dẫn)\b',
                r'\b(làm sao|như thế nào)\s+để',
                r'\bhelp\s+\w+'
            ]
        }
    
    def classify_intent(self, text: str) -> IntentResult:
        """Phân loại intent từ văn bản"""
        if not text:
            return IntentResult(IntentType.UNKNOWN, 0.0, [], {}, text)
        
        # Chuẩn hóa văn bản
        normalized_text = self.text_processor.normalize_text(text)
        expanded_text = self.text_processor.expand_synonyms(normalized_text)
        
        best_intent = IntentType.UNKNOWN
        best_confidence = 0.0
        matched_entities = []
        
        # Kiểm tra từng intent theo thứ tự ưu tiên
        intent_priority = {
            IntentType.ORDER: 10,
            IntentType.SEARCH_BY_PRICE: 9,     # Tăng ưu tiên cho search by price
            IntentType.QUERY: 8,               # Giảm ưu tiên cho query
            IntentType.RECOMMEND: 7,           # Giảm ưu tiên cho recommend
            IntentType.SEARCH_BY_CATEGORY: 6,  # Giảm ưu tiên cho category
            IntentType.SEARCH_BY_AUTHOR: 5,    # Giảm ưu tiên cho author
            IntentType.SEARCH_BY_TITLE: 4,
            IntentType.RECOMMEND_BY_PRICE: 3,
            IntentType.LIST_CATEGORIES: 2,
            IntentType.CHECK_STOCK: 1,
            IntentType.GREETING: 0,
            IntentType.GOODBYE: 0,
            IntentType.HELP: 0
        }
        
        # Sắp xếp intents theo độ ưu tiên
        sorted_intents = sorted(self.intent_patterns.items(), 
                              key=lambda x: intent_priority.get(x[0], 0), reverse=True)
        
        for intent_type, patterns in sorted_intents:
            for pattern in patterns:
                matches = re.finditer(pattern, expanded_text, re.IGNORECASE)
                for match in matches:
                    confidence = self._calculate_confidence(match, expanded_text)
                    # Ưu tiên intent có độ ưu tiên cao hơn nếu confidence gần bằng nhau
                    priority_bonus = intent_priority.get(intent_type, 0) * 0.01
                    adjusted_confidence = confidence + priority_bonus
                    
                    if adjusted_confidence > best_confidence:
                        best_confidence = adjusted_confidence
                        best_intent = intent_type
                        # Chỉ thêm entity mới nếu chưa có
                        if not any(e.value == match.group() for e in matched_entities):
                            matched_entities.append(ExtractedEntity(
                                value=match.group(),
                                confidence=confidence,
                                start_pos=match.start(),
                                end_pos=match.end(),
                                entity_type=intent_type.value
                            ))
        
        # Trích xuất parameters
        parameters = self._extract_parameters(expanded_text, best_intent)
        
        return IntentResult(
            intent=best_intent,
            confidence=best_confidence,
            entities=matched_entities,
            parameters=parameters,
            original_text=text
        )
    
    def _calculate_confidence(self, match: re.Match, text: str) -> float:
        """Tính toán độ tin cậy của match"""
        match_length = len(match.group())
        text_length = len(text)
        
        # Độ tin cậy cơ bản dựa trên độ dài match (ưu tiên match dài hơn)
        base_confidence = min(0.7, match_length / text_length * 2) if text_length > 0 else 0.5
        
        # Bonus cho từ khóa quan trọng
        keyword_bonus = 0.0
        match_text = match.group().lower()
        if any(keyword in match_text for keyword in ['đặt', 'mua', 'giá', 'tìm', 'gợi ý', 'cửa hàng', 'sách', 'của', 'tác giả', 'viết bởi']):
            keyword_bonus = 0.4
        
        # Bonus cho vị trí match (ưu tiên đầu câu)
        position_bonus = 0.0
        if match.start() < text_length * 0.5:  # Nếu match ở nửa đầu câu
            position_bonus = 0.2
        
        # Bonus cho match dài hơn (ưu tiên specificity)
        length_bonus = 0.0
        if match_length > 10:  # Match dài hơn 10 ký tự
            length_bonus = 0.1
        
        confidence = min(1.0, base_confidence + keyword_bonus + position_bonus + length_bonus)
        return confidence
    
    def _extract_parameters(self, text: str, intent: IntentType) -> Dict[str, Any]:
        """Trích xuất parameters từ văn bản dựa trên intent"""
        parameters = {}
        
        if intent == IntentType.ORDER:
            parameters.update(self._extract_order_parameters(text))
        elif intent == IntentType.QUERY:
            parameters.update(self._extract_query_parameters(text))
        elif intent == IntentType.SEARCH_BY_PRICE:
            parameters.update(self._extract_price_parameters(text))
        elif intent == IntentType.SEARCH_BY_AUTHOR:
            parameters.update(self._extract_author_parameters(text))
        elif intent == IntentType.SEARCH_BY_CATEGORY:
            parameters.update(self._extract_category_parameters(text))
        elif intent == IntentType.RECOMMEND_BY_PRICE:
            parameters.update(self._extract_price_parameters(text))
        
        return parameters
    
    def _extract_order_parameters(self, text: str) -> Dict[str, Any]:
        """Trích xuất parameters cho đặt hàng"""
        params = {}
        
        # Trích xuất số lượng
        quantity_match = re.search(r'\b(\d+)\b', text)
        if quantity_match:
            params['quantity'] = int(quantity_match.group(1))
        
        # Trích xuất địa chỉ và số điện thoại
        address_phone_match = re.search(r'(.+?),\s*(\d{9,11})', text)
        if address_phone_match:
            params['address'] = address_phone_match.group(1).strip()
            params['phone'] = address_phone_match.group(2).strip()
        
        return params
    
    def _extract_query_parameters(self, text: str) -> Dict[str, Any]:
        """Trích xuất parameters cho truy vấn"""
        params = {}
        
        # Kiểm tra xem có phải chỉ hỏi giá không
        if 'giá' in text or 'giá bao nhiêu' in text:
            params['is_price_only'] = True
        elif 'có bao nhiêu sách' in text or 'có bao nhiêu cuốn' in text or 'tồn kho' in text or 'còn bao nhiêu' in text:
            params['is_stock_only'] = True
        elif 'bao nhiêu' in text and ('giá' in text or 'tiền' in text):
            params['is_price_only'] = True
        
        return params
    
    def _extract_price_parameters(self, text: str) -> Dict[str, Any]:
        """Trích xuất parameters cho tìm kiếm theo giá"""
        params = {}
        
        # Pattern 1: "giá từ A đến B"
        range_match = re.search(r'giá\s+từ\s*(\d+)\s*đến\s*(\d+)', text, re.IGNORECASE)
        if range_match:
            params['price_range'] = (int(range_match.group(1)), int(range_match.group(2)))
            return params
        
        # Pattern 2: "từ A đến B" (không có "giá")
        range_match = re.search(r'từ\s*(\d+)\s*đến\s*(\d+)', text, re.IGNORECASE)
        if range_match:
            params['price_range'] = (int(range_match.group(1)), int(range_match.group(2)))
            return params
        
        # Pattern 3: "giá dưới X", "giá từ X", "giá trên X"
        single_match = re.search(r'giá\s+(dưới|từ|trên|cao hơn|thấp hơn)\s*(\d+)', text, re.IGNORECASE)
        if single_match:
            keyword = single_match.group(1).lower()
            number = int(single_match.group(2))
            if keyword in ['dưới', 'thấp hơn']:
                params['price_range'] = (None, number)
            elif keyword in ['từ', 'trên', 'cao hơn']:
                params['price_range'] = (number, None)
            return params
        
        # Pattern 4: "dưới X VND", "từ X VND", "trên X VND"
        vnd_match = re.search(r'(dưới|từ|trên)\s*(\d+)\s*VND', text, re.IGNORECASE)
        if vnd_match:
            keyword = vnd_match.group(1).lower()
            number = int(vnd_match.group(2))
            if keyword == 'dưới':
                params['price_range'] = (None, number)
            elif keyword in ['từ', 'trên']:
                params['price_range'] = (number, None)
            return params
        
        # Pattern 5: "trên X", "cao hơn X" (không có VND)
        above_match = re.search(r'(trên|cao hơn)\s*(\d+)', text, re.IGNORECASE)
        if above_match:
            number = int(above_match.group(2))
            params['price_range'] = (number, None)
            return params
        
        # Pattern 6: "dưới X", "thấp hơn X" (không có VND)
        below_match = re.search(r'(dưới|thấp hơn)\s*(\d+)', text, re.IGNORECASE)
        if below_match:
            number = int(below_match.group(2))
            params['price_range'] = (None, number)
            return params
        
        return params
    
    def _extract_author_parameters(self, text: str) -> Dict[str, Any]:
        """Trích xuất parameters cho tìm kiếm theo tác giả"""
        params = {}
        
        # Debug logging
        print(f"DEBUG - Extracting author from: '{text}'")
        
        # Tìm tên tác giả sau từ khóa
        author_match = re.search(r'(tác giả|sách của|viết bởi)\s+([\w\s]+?)(?:\s+(?:có|không)\b|\?|$)', text, re.IGNORECASE)
        if author_match:
            params['author'] = author_match.group(2).strip()
            print(f"DEBUG - Found author via pattern: '{params['author']}'")
        else:
            # Fallback: lấy từ cuối câu (loại bỏ từ "sách" nếu có)
            words = text.split()
            if len(words) > 1:
                # Loại bỏ từ "sách" ở đầu nếu có
                if words[0].lower() in ['sách', 'cuốn', 'quyển']:
                    words = words[1:]
                if len(words) >= 2:
                    params['author'] = ' '.join(words)  # Lấy tất cả từ còn lại
                elif len(words) == 1:
                    params['author'] = words[0]
                print(f"DEBUG - Found author via fallback: '{params.get('author', 'None')}'")
        
        return params
    
    def _extract_category_parameters(self, text: str) -> Dict[str, Any]:
        """Trích xuất parameters cho tìm kiếm theo thể loại"""
        params = {}
        
        # Tìm thể loại sau từ khóa
        category_match = re.search(r'(sách về|thể loại|loại)\s+([\w\s]+?)(?:\s+(?:có|những|cuốn|gì)\b|\?|$)', text, re.IGNORECASE)
        if category_match:
            params['category'] = category_match.group(2).strip()
        else:
            # Fallback: lấy từ cuối câu
            words = text.split()
            if len(words) > 1:
                params['category'] = ' '.join(words[-2:])  # Lấy 2 từ cuối
        
        return params

class EntityExtractor:
    """Trích xuất entities từ văn bản với fuzzy matching"""
    
    def __init__(self, books_data: List[Dict] = None):
        self.books_data = books_data or []
        self.text_processor = VietnameseTextProcessor()
        self._build_search_indexes()
    
    def _build_search_indexes(self):
        """Xây dựng index để tìm kiếm nhanh"""
        self.title_index = {}
        self.author_index = {}
        self.category_index = {}
        
        for book in self.books_data:
            title = book.get('title', '').strip().lower()
            author = book.get('author', '').strip().lower()
            category = book.get('category', '').strip().lower()
            
            if title:
                # Tạo các biến thể của title
                title_variants = [title]
                # Loại bỏ dấu câu
                title_clean = re.sub(r'[^\w\s]', '', title)
                if title_clean != title:
                    title_variants.append(title_clean)
                
                for variant in title_variants:
                    self.title_index[variant] = book
            
            if author:
                self.author_index[author] = book
            
            if category:
                self.category_index[category] = book
    
    def extract_book_title(self, text: str, threshold: int = 80) -> Optional[str]:
        """Trích xuất tên sách từ văn bản với fuzzy matching"""
        if not self.books_data:
            return None
        
        text_lower = text.lower()
        
        # Sắp xếp candidates theo độ dài (dài hơn trước) để tránh match sai
        candidates = [book for book in self.books_data if book.get('title')]
        candidates.sort(key=lambda x: len(x.get('title', '')), reverse=True)
        
        for book in candidates:
            title = book.get('title', '').strip()
            if not title:
                continue
            
            title_lower = title.lower()
            
            # Tìm kiếm với word boundaries (ưu tiên cao nhất)
            escaped_title = re.escape(title_lower)
            pattern = r"\b" + escaped_title + r"\b"
            if re.search(pattern, text_lower):
                return title
            
            # Fallback: exact match without word boundaries
            if title_lower in text_lower:
                return title
        
        # Fuzzy matching nếu không tìm thấy chính xác
        book_titles = [book.get('title', '').strip() for book in self.books_data if book.get('title')]
        
        if book_titles:
            # Tìm kiếm fuzzy với threshold thấp hơn cho partial matching
            best_match = process.extractOne(text, book_titles, scorer=fuzz.partial_ratio)
            
            if best_match and best_match[1] >= 60:  # Giảm threshold xuống 60
                return best_match[0]
        
        return None
    
    def extract_author_fuzzy(self, text: str, threshold: int = 80) -> Optional[str]:
        """Trích xuất tác giả với fuzzy matching"""
        if not self.books_data:
            return None
        
        normalized_text = self.text_processor.normalize_text(text)
        
        # Tìm kiếm chính xác trước
        for author, book in self.author_index.items():
            if author in normalized_text:
                return book.get('author', '').strip()
        
        # Fuzzy matching
        authors = [book.get('author', '').strip() for book in self.books_data if book.get('author')]
        
        if authors:
            best_match = process.extractOne(normalized_text, authors, scorer=fuzz.partial_ratio)
            
            if best_match and best_match[1] >= threshold:
                return best_match[0]
        
        return None
    
    def extract_category_fuzzy(self, text: str, threshold: int = 80) -> Optional[str]:
        """Trích xuất thể loại với fuzzy matching"""
        if not self.books_data:
            return None
        
        normalized_text = self.text_processor.normalize_text(text)
        
        # Tìm kiếm chính xác trước
        for category, book in self.category_index.items():
            if category in normalized_text:
                return book.get('category', '').strip()
        
        # Fuzzy matching
        categories = [book.get('category', '').strip() for book in self.books_data if book.get('category')]
        
        if categories:
            best_match = process.extractOne(normalized_text, categories, scorer=fuzz.partial_ratio)
            
            if best_match and best_match[1] >= threshold:
                return best_match[0]
        
        return None
    
    def extract_quantity(self, text: str) -> Optional[int]:
        """Trích xuất số lượng từ văn bản"""
        match = re.search(r'\b(\d+)\b', text)
        return int(match.group(1)) if match else None
    
    def extract_phone_number(self, text: str) -> Optional[str]:
        """Trích xuất số điện thoại từ văn bản"""
        # Pattern cho số điện thoại Việt Nam
        phone_patterns = [
            r'(\d{10,11})',  # 10-11 chữ số
            r'(\+84\d{9,10})',  # +84 + 9-10 chữ số
            r'(0\d{9,10})'  # 0 + 9-10 chữ số
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def extract_address(self, text: str) -> Optional[str]:
        """Trích xuất địa chỉ từ văn bản"""
        # Loại bỏ số điện thoại khỏi địa chỉ
        text_without_phone = re.sub(r'\d{9,11}', '', text)
        
        # Tìm địa chỉ (thường có từ khóa địa chỉ)
        address_keywords = ['địa chỉ', 'address', 'tại', 'ở', 'số', 'đường', 'phố', 'quận', 'huyện', 'tỉnh', 'thành phố']
        
        for keyword in address_keywords:
            if keyword in text_without_phone.lower():
                # Lấy phần sau từ khóa
                parts = text_without_phone.lower().split(keyword)
                if len(parts) > 1:
                    address = parts[1].strip()
                    # Loại bỏ dấu câu thừa
                    address = re.sub(r'[^\w\s]', ' ', address).strip()
                    if address:
                        return address
        
        # Fallback: lấy toàn bộ text nếu không tìm thấy từ khóa
        return text_without_phone.strip() if text_without_phone.strip() else None

class NLProcessor:
    """Lớp chính xử lý NLP cho chatbot với các tính năng thông minh"""
    
    def __init__(self, books_data: List[Dict] = None):
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor(books_data)
        self.text_processor = VietnameseTextProcessor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.context_manager = ContextManager()
    
    def process_input(self, text: str, session_id: str = None) -> IntentResult:
        """Xử lý đầu vào và trả về kết quả phân tích với context"""
        if not text:
            return IntentResult(IntentType.UNKNOWN, 0.0, [], {}, text)
        
        # Phân tích cảm xúc
        sentiment = self.sentiment_analyzer.analyze_sentiment(text)
        
        # Phân loại intent
        intent_result = self.intent_classifier.classify_intent(text)
        intent_result.sentiment = sentiment
        
        # Cải thiện intent dựa trên context
        if session_id:
            context = self.context_manager.get_context(session_id)
            intent_result = self._improve_intent_with_context(intent_result, context)
        
        # Trích xuất entities bổ sung với fuzzy matching
        additional_entities = self._extract_additional_entities(text, intent_result.intent)
        intent_result.entities.extend(additional_entities)
        
        # Cập nhật parameters với entities (preserve existing parameters)
        entity_params = self._extract_parameters_from_entities(intent_result)
        intent_result.parameters.update(entity_params)
        
        # Cập nhật context
        if session_id:
            self.context_manager.update_context(session_id, text, intent_result)
            intent_result.context = {
                'session_id': session_id,
                'user_preferences': context.user_preferences,
                'current_topic': context.current_topic,
                'last_intent': context.last_intent,
                'smart_suggestions': self.context_manager.get_smart_suggestions(session_id, intent_result.intent)
            }
        
        return intent_result
    
    def _improve_intent_with_context(self, intent_result: IntentResult, context: ConversationContext) -> IntentResult:
        """Cải thiện intent dựa trên context"""
        # Nếu intent không chắc chắn, sử dụng context để cải thiện
        if intent_result.confidence < 0.7 and context.last_intent:
            # Nếu người dùng đang trong flow đặt hàng
            if context.last_intent == IntentType.ORDER:
                if any(word in intent_result.original_text.lower() for word in ['có', 'đồng ý', 'ok']):
                    intent_result.intent = IntentType.ORDER
                    intent_result.confidence = 0.9
                elif any(word in intent_result.original_text.lower() for word in ['không', 'hủy', 'cancel']):
                    intent_result.intent = IntentType.ORDER
                    intent_result.confidence = 0.9
            
            # Nếu người dùng đang tìm kiếm theo thể loại
            elif context.last_intent == IntentType.SEARCH_BY_CATEGORY:
                if context.current_topic:
                    intent_result.parameters['category'] = context.current_topic
                    intent_result.confidence = min(1.0, intent_result.confidence + 0.2)
        
        return intent_result
    
    def _extract_additional_entities(self, text: str, intent: IntentType) -> List[ExtractedEntity]:
        """Trích xuất entities bổ sung dựa trên intent với fuzzy matching"""
        entities = []
        
        if intent in [IntentType.ORDER, IntentType.QUERY, IntentType.SEARCH_BY_TITLE]:
            # Trích xuất tên sách với fuzzy matching
            book_title = self.entity_extractor.extract_book_title(text)
            if book_title:
                entities.append(ExtractedEntity(
                    value=book_title,
                    confidence=0.9,
                    start_pos=0,
                    end_pos=len(book_title),
                    entity_type='book_title'
                ))
        
        if intent == IntentType.SEARCH_BY_AUTHOR:
            # Trích xuất tác giả với fuzzy matching
            author = self.entity_extractor.extract_author_fuzzy(text)
            print(f"DEBUG - Extracted author entity: '{author}'")
            if author:
                entities.append(ExtractedEntity(
                    value=author,
                    confidence=0.9,
                    start_pos=0,
                    end_pos=len(author),
                    entity_type='author'
                ))
        
        if intent == IntentType.SEARCH_BY_CATEGORY:
            # Trích xuất thể loại với fuzzy matching
            category = self.entity_extractor.extract_category_fuzzy(text)
            if category:
                entities.append(ExtractedEntity(
                    value=category,
                    confidence=0.9,
                    start_pos=0,
                    end_pos=len(category),
                    entity_type='category'
                ))
        
        if intent == IntentType.ORDER:
            # Trích xuất số lượng
            quantity = self.entity_extractor.extract_quantity(text)
            if quantity:
                entities.append(ExtractedEntity(
                    value=str(quantity),
                    confidence=0.8,
                    start_pos=0,
                    end_pos=len(str(quantity)),
                    entity_type='quantity'
                ))
            
            # Trích xuất số điện thoại
            phone = self.entity_extractor.extract_phone_number(text)
            if phone:
                entities.append(ExtractedEntity(
                    value=phone,
                    confidence=0.9,
                    start_pos=0,
                    end_pos=len(phone),
                    entity_type='phone'
                ))
            
            # Trích xuất địa chỉ
            address = self.entity_extractor.extract_address(text)
            if address:
                entities.append(ExtractedEntity(
                    value=address,
                    confidence=0.7,
                    start_pos=0,
                    end_pos=len(address),
                    entity_type='address'
                ))
        
        return entities
    
    def _extract_parameters_from_entities(self, intent_result: IntentResult) -> Dict[str, Any]:
        """Trích xuất parameters từ entities"""
        params = {}
        
        for entity in intent_result.entities:
            if entity.entity_type == 'book_title':
                params['book_title'] = entity.value
            elif entity.entity_type == 'quantity':
                params['quantity'] = int(entity.value)
            elif entity.entity_type == 'phone':
                params['phone'] = entity.value
            elif entity.entity_type == 'address':
                params['address'] = entity.value
        
        return params
    
    def update_books_data(self, books_data: List[Dict]):
        """Cập nhật dữ liệu sách cho entity extractor"""
        self.entity_extractor.books_data = books_data
        self.entity_extractor._build_search_indexes()
    
    def get_user_preferences(self, session_id: str) -> Dict[str, Any]:
        """Lấy sở thích người dùng"""
        context = self.context_manager.get_context(session_id)
        return context.user_preferences
    
    def get_conversation_context(self, session_id: str) -> ConversationContext:
        """Lấy context của cuộc hội thoại"""
        return self.context_manager.get_context(session_id)
    
    def clear_context(self, session_id: str):
        """Xóa context của session"""
        if session_id in self.context_manager.contexts:
            del self.context_manager.contexts[session_id]
    
    def get_smart_suggestions(self, session_id: str, current_intent: IntentType) -> List[str]:
        """Lấy gợi ý thông minh"""
        return self.context_manager.get_smart_suggestions(session_id, current_intent)

# Singleton instance
nlp_processor = NLProcessor()
