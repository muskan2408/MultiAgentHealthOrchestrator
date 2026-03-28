from src.models.schemas import UserMessage
from src.orchestrator.orchestrator import Orchestrator


def main() -> None:
    print("\n--- mama health AI assistant ---")
    print("Type your health question and press Enter.")
    print("Type 'quit' to exit.\n")

    orchestrator = Orchestrator()
    session_id = "cli-session"

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        message = UserMessage(text=user_input, session_id=session_id)
        response = orchestrator.process(message)

        print(f"\n[{response.agent.value.upper()} AGENT]\n{response.text}\n")

        if response.should_escalate:
            print("*** Please seek emergency care immediately if needed ***\n")

def run_cli() -> None:
    main()
