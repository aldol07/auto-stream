import os
import sys
from pathlib import Path

from .stdio_fix import apply_stdio_utf8

apply_stdio_utf8()

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

from .agent import build_graph, get_initial_state


class Colors:
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    MAGENTA = "\033[95m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"
    DIM     = "\033[2m"


def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════╗
║              AutoStream AI Sales Agent               ║
║      Powered by LangGraph + Gemini 1.5 Flash         ║
╚══════════════════════════════════════════════════════╝
{Colors.RESET}
{Colors.DIM}Type your message and press Enter. Type 'exit' or 'quit' to stop.
Type 'reset' to start a new conversation.
{Colors.RESET}"""
    print(banner)


def print_agent_response(text: str):
    print(f"\n{Colors.GREEN}{Colors.BOLD}AutoStream Agent:{Colors.RESET}")
    print(f"{Colors.GREEN}{text}{Colors.RESET}\n")


def print_user_input_prompt():
    return input(f"{Colors.YELLOW}{Colors.BOLD}You: {Colors.RESET}")


def print_intent_debug(intent: str):
    """Optional: show intent classification for debugging."""
    color = {
        "greeting": Colors.CYAN,
        "product_inquiry": Colors.MAGENTA,
        "high_intent": Colors.YELLOW,
    }.get(intent, Colors.DIM)
    print(f"{Colors.DIM}  [Intent: {color}{intent}{Colors.RESET}{Colors.DIM}]{Colors.RESET}")


def run_agent():
    """Main interactive loop for the AutoStream agent."""
    
    # Validate API key
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(f"\n{Colors.YELLOW}ERROR: No API key found.")
        print("Please create a .env file in the project root with: GEMINI_API_KEY=your_key_here")
        print(f"Get a free key at: https://aistudio.google.com/app/apikey{Colors.RESET}\n")
        sys.exit(1)
    
    print_banner()
    
    # Build the LangGraph graph
    print(f"{Colors.DIM}Initializing agent...{Colors.RESET}", end="", flush=True)
    graph = build_graph()
    state = get_initial_state()
    print(f"\r{Colors.GREEN}Agent ready.{Colors.RESET}           \n")
    
    # Show debug mode option
    debug_mode = "--debug" in sys.argv
    if debug_mode:
        print(f"{Colors.DIM}[Debug mode enabled - showing intent classifications]{Colors.RESET}\n")
    
    # Warm greeting
    print_agent_response(
        "Hi! I'm the AutoStream AI assistant.\n"
        "AutoStream helps content creators edit videos automatically with AI - "
        "faster, smarter, and in stunning 4K.\n\n"
        "How can I help you today? Feel free to ask about our plans, features, or pricing!"
    )
    
    # ── Main conversation loop ──
    while True:
        try:
            user_input = print_user_input_prompt()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n{Colors.DIM}Goodbye.{Colors.RESET}\n")
            break
        
        user_input = user_input.strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ("exit", "quit", "bye", "goodbye"):
            print_agent_response("Thanks for chatting. Goodbye.")
            break
        
        if user_input.lower() == "reset":
            state = get_initial_state()
            print(f"\n{Colors.DIM}[Conversation reset]{Colors.RESET}\n")
            print_agent_response("Sure! Let's start fresh. How can I help you with AutoStream today?")
            continue
        
        if user_input.lower() == "leads":
            _show_leads_log()
            continue
        
        # ── Invoke the graph ──
        state["messages"] = state["messages"] + [HumanMessage(content=user_input)]
        
        try:
            result = graph.invoke(state)
            state = result
            
            # Show intent in debug mode
            if debug_mode and "intent" in state:
                print_intent_debug(state["intent"])
            
            # Extract and display the latest AI response
            from langchain_core.messages import AIMessage
            ai_messages = [m for m in state["messages"] if isinstance(m, AIMessage)]
            if ai_messages:
                latest_response = ai_messages[-1].content
                print_agent_response(latest_response)
            
            # If lead was just captured, show celebration
            if state.get("lead_captured"):
                print(f"{Colors.DIM}[Lead successfully logged to backend/leads_log.json]{Colors.RESET}\n")
        
        except Exception as e:
            print(f"\n{Colors.YELLOW}Error: {e}{Colors.RESET}")
            print(f"{Colors.DIM}Please check your API key and try again.{Colors.RESET}\n")


def _show_leads_log():
    """Display captured leads from the log file."""
    import json
    from pathlib import Path

    log_path = Path(__file__).parent / "leads_log.json"
    
    if not log_path.exists():
        print(f"\n{Colors.DIM}No leads captured yet.{Colors.RESET}\n")
        return
    
    with open(log_path) as f:
        leads = json.load(f)
    
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}Captured Leads ({len(leads)} total):{Colors.RESET}")
    for lead in leads:
        print(f"  • {lead['name']} | {lead['email']} | {lead['platform']} | {lead['captured_at']}")
    print()


