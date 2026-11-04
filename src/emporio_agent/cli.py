import argparse
import os
from pathlib import Path

from .agent import Agent
from .data_store import load_data
from .llm import client_from_environment
from .memory import SessionMemory


def main() -> None:
    parser = argparse.ArgumentParser(description="Tom, Empório da Música customer-support agent")
    parser.add_argument("--data", default="Desafio Técnico AI Engineer 2026/data")
    parser.add_argument("--session", default="default")
    parser.add_argument("--memory-dir", default=".sessions")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    memory_path = Path(args.memory_dir) / f"{args.session}.json"
    agent = Agent(client_from_environment(), load_data(args.data), SessionMemory.load(memory_path), args.session, args.debug)
    print("Tom: Hi! How can I help with music today? (type 'exit' to quit)")
    while True:
        try:
            message = input("You: ").strip()
        except EOFError:
            break
        if message.casefold() in {"exit", "quit"}:
            break
        if not message:
            continue
        print(f"Tom: {agent.respond(message)}")
        agent.memory.save(memory_path)


if __name__ == "__main__":
    main()
