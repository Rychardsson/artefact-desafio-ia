import argparse
import os
from pathlib import Path

from .agent import Agent
from .data_store import load_data
from .llm import client_from_environment
from .memory import SessionMemory


def main() -> None:
    parser = argparse.ArgumentParser(description="Tom, agente do Empório da Música")
    parser.add_argument("--data", default="Desafio Técnico AI Engineer 2026/data")
    parser.add_argument("--session", default="default")
    parser.add_argument("--memory-dir", default=".sessions")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    memory_path = Path(args.memory_dir) / f"{args.session}.json"
    agent = Agent(client_from_environment(), load_data(args.data), SessionMemory.load(memory_path), args.session, args.debug)
    print("Tom: Oi! Como posso ajudar com música hoje? (digite 'sair' para encerrar)")
    while True:
        try:
            message = input("Você: ").strip()
        except EOFError:
            break
        if message.casefold() in {"sair", "exit", "quit"}:
            break
        if not message:
            continue
        print(f"Tom: {agent.respond(message)}")
        agent.memory.save(memory_path)


if __name__ == "__main__":
    main()
