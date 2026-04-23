"""
AutoStream Conversational AI Agent
Built with LangGraph for ServiceHive Inflx Assignment
"""

import os
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from .rag_pipeline import retrieve_context
from .tools import mock_lead_capture
from .intent_classifier import classify_intent


# ─────────────────────────────────────────────
# STATE DEFINITION
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # Full conversation history
    intent: str                                # Current classified intent
    lead_name: str | None                      # Collected lead: name
    lead_email: str | None                     # Collected lead: email
    lead_platform: str | None                  # Collected lead: platform
    lead_captured: bool                        # Whether lead was submitted
    awaiting_lead_field: str | None            # Which field we're asking for next


# ─────────────────────────────────────────────
# LLM SETUP
# ─────────────────────────────────────────────

def get_llm():
    raw = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    api_key = raw.strip() if raw else ""
    if not api_key:
        raise ValueError(
            "No API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY (e.g. on your API host’s environment, not the static site)."
        )
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.3,
    )


# ─────────────────────────────────────────────
# NODE: INTENT ROUTER
# ─────────────────────────────────────────────

def intent_router_node(state: AgentState) -> AgentState:
    """Classifies the latest user message intent."""
    last_message = state["messages"][-1]
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)
    
    intent = classify_intent(user_text, get_llm())
    return {**state, "intent": intent}


# ─────────────────────────────────────────────
# NODE: GREETING
# ─────────────────────────────────────────────

def greeting_node(state: AgentState) -> AgentState:
    """Handles casual greetings."""
    llm = get_llm()
    system_prompt = """You are an AI assistant for AutoStream, a SaaS video editing platform for content creators.
You are warm, friendly, and helpful. The user just sent a casual greeting.
Respond warmly, introduce yourself briefly, and invite them to ask about AutoStream's features or pricing.
Keep it concise (2-3 sentences)."""
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *state["messages"]
    ])
    
    return {**state, "messages": state["messages"] + [AIMessage(content=response.content)]}


# ─────────────────────────────────────────────
# NODE: RAG RETRIEVAL + RESPONSE
# ─────────────────────────────────────────────

def rag_node(state: AgentState) -> AgentState:
    """Retrieves relevant knowledge and generates a response."""
    llm = get_llm()
    last_message = state["messages"][-1]
    user_query = last_message.content if hasattr(last_message, "content") else str(last_message)
    
    # Retrieve relevant context from knowledge base
    context = retrieve_context(user_query)
    
    system_prompt = f"""You are an AI assistant for AutoStream, a SaaS video editing platform.
Use ONLY the following knowledge base context to answer the user's question accurately.
If the answer is not in the context, say you'll connect them with support.

KNOWLEDGE BASE CONTEXT:
{context}

Instructions:
- Be concise and helpful
- Mention specific prices/features accurately from the context
- After answering, subtly ask if they'd like to get started or have more questions
- Never make up information not in the context"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *state["messages"]
    ])
    
    return {**state, "messages": state["messages"] + [AIMessage(content=response.content)]}


# ─────────────────────────────────────────────
# NODE: LEAD COLLECTION
# ─────────────────────────────────────────────

def lead_collection_node(state: AgentState) -> AgentState:
    """Collects lead information step by step. Calls tool only when all fields collected."""
    
    name = state.get("lead_name")
    email = state.get("lead_email")
    platform = state.get("lead_platform")
    awaiting = state.get("awaiting_lead_field")
    messages = state["messages"]

    # ── Parse the user's last reply into the field we were awaiting ──
    last_message = messages[-1]
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    if awaiting == "name":
        name = user_text.strip()
        awaiting = None
    elif awaiting == "email":
        email = user_text.strip()
        awaiting = None
    elif awaiting == "platform":
        platform = user_text.strip()
        awaiting = None

    # ── Decide what to ask for next ──
    if not name:
        response_text = "Great, I'd love to get you started with AutoStream! 🎬\n\nCould you please share your **full name**?"
        awaiting = "name"

    elif not email:
        response_text = f"Nice to meet you, {name}! 👋\n\nWhat's your **email address** so we can set up your account?"
        awaiting = "email"

    elif not platform:
        response_text = f"Perfect! Last question — which **creator platform** do you primarily use? (e.g., YouTube, Instagram, TikTok, etc.)"
        awaiting = "platform"

    else:
        # ── ALL INFO COLLECTED → fire the tool ──
        mock_lead_capture(name, email, platform)
        response_text = (
            f"🎉 You're all set, **{name}**!\n\n"
            f"We've captured your details and our team will reach out to **{email}** shortly "
            f"to set up your AutoStream Pro account for **{platform}**.\n\n"
            f"Welcome aboard! 🚀"
        )
        return {
            **state,
            "messages": messages + [AIMessage(content=response_text)],
            "lead_name": name,
            "lead_email": email,
            "lead_platform": platform,
            "lead_captured": True,
            "awaiting_lead_field": None,
        }

    return {
        **state,
        "messages": messages + [AIMessage(content=response_text)],
        "lead_name": name,
        "lead_email": email,
        "lead_platform": platform,
        "lead_captured": False,
        "awaiting_lead_field": awaiting,
    }


# ─────────────────────────────────────────────
# ROUTING LOGIC
# ─────────────────────────────────────────────

def route_after_intent(state: AgentState) -> Literal["greeting", "rag", "lead_collection"]:
    """Routes to the correct node based on classified intent."""
    
    # If we're mid-lead-collection, always continue collecting
    if state.get("awaiting_lead_field") or (
        state.get("lead_name") and not state.get("lead_captured")
    ):
        return "lead_collection"
    
    intent = state.get("intent", "greeting")
    
    if intent == "high_intent":
        return "lead_collection"
    elif intent == "product_inquiry":
        return "rag"
    else:
        return "greeting"


# ─────────────────────────────────────────────
# BUILD THE GRAPH
# ─────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("greeting", greeting_node)
    graph.add_node("rag", rag_node)
    graph.add_node("lead_collection", lead_collection_node)

    # Entry point
    graph.set_entry_point("intent_router")

    # Routing from intent_router
    graph.add_conditional_edges(
        "intent_router",
        route_after_intent,
        {
            "greeting": "greeting",
            "rag": "rag",
            "lead_collection": "lead_collection",
        }
    )

    # All response nodes → END (wait for next user input)
    graph.add_edge("greeting", END)
    graph.add_edge("rag", END)
    graph.add_edge("lead_collection", END)

    return graph.compile()


# ─────────────────────────────────────────────
# INITIAL STATE
# ─────────────────────────────────────────────

def get_initial_state() -> AgentState:
    return {
        "messages": [],
        "intent": "greeting",
        "lead_name": None,
        "lead_email": None,
        "lead_platform": None,
        "lead_captured": False,
        "awaiting_lead_field": None,
    }
