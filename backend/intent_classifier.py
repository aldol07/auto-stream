"""
Intent Classifier for AutoStream Agent
Classifies user messages into: greeting | product_inquiry | high_intent
"""

from langchain_core.messages import HumanMessage, SystemMessage


INTENT_SYSTEM_PROMPT = """You are an intent classifier for AutoStream, a SaaS video editing platform.

Classify the user's message into EXACTLY ONE of these three categories:

1. "greeting"
   - Casual hello, hi, hey, how are you
   - General small talk with no product interest
   - Example: "Hi there!", "Hello!", "What's up?"

2. "product_inquiry"
   - Asking about features, pricing, plans, policies, how it works
   - Comparing plans, asking about specific features
   - Example: "How much does the Pro plan cost?", "Do you support 4K?", "What's your refund policy?"

3. "high_intent"
   - Expressing desire to sign up, try, purchase, or get started
   - Mentioning they want a specific plan
   - Phrases like: "I want to try", "I'd like to sign up", "Let's do it", "I'm interested in buying"
   - Example: "I want to try the Pro plan", "Sign me up!", "I'm ready to get started"

RULES:
- Respond with ONLY the category label, nothing else
- No punctuation, no explanation
- Must be one of: greeting, product_inquiry, high_intent"""


def classify_intent(user_message: str, llm) -> str:
    """
    Classify user message intent using the LLM.
    Returns: 'greeting' | 'product_inquiry' | 'high_intent'
    """
    response = llm.invoke([
        SystemMessage(content=INTENT_SYSTEM_PROMPT),
        HumanMessage(content=user_message)
    ])
    
    raw = response.content.strip().lower()
    
    # Normalize to valid intent
    if "high_intent" in raw or "high intent" in raw:
        return "high_intent"
    elif "product" in raw or "inquiry" in raw:
        return "product_inquiry"
    elif "greeting" in raw:
        return "greeting"
    else:
        # Fallback: try keyword matching
        return _keyword_fallback(user_message)


def _keyword_fallback(text: str) -> str:
    """Keyword-based fallback intent detection."""
    text_lower = text.lower()
    
    high_intent_keywords = [
        "sign up", "signup", "register", "subscribe", "buy", "purchase",
        "want to try", "get started", "i'm in", "let's do it", "ready",
        "interested in", "i'll take", "pro plan", "basic plan"
    ]
    
    product_keywords = [
        "price", "pricing", "cost", "plan", "feature", "how much",
        "what is", "tell me about", "refund", "support", "resolution",
        "4k", "720p", "unlimited", "caption", "video"
    ]
    
    for kw in high_intent_keywords:
        if kw in text_lower:
            return "high_intent"
    
    for kw in product_keywords:
        if kw in text_lower:
            return "product_inquiry"
    
    return "greeting"
