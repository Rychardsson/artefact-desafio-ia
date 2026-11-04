# Empório da Música Customer Support Agent

Python customer-support agent for the Empório da Música catalog, pricing, orders, policies, and human handoff.

## Running

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
Copy-Item .env.example .env
# set EMPORIO_API_KEY in the environment or in .env
uv run emporio-agent
```

The CLI accepts:

```text
--data        CSV data directory
--session     persisted session name
--memory-dir  session JSON directory
--debug       show tool names called by the agent
```

The CLI loads `.env` automatically. To configure the provider explicitly in PowerShell:

```powershell
$env:EMPORIO_API_KEY = "your-key"
uv run emporio-agent --debug
```

To validate without an external provider:

```powershell
uv run --with pytest pytest
```

## Architecture

```text
CLI
 └── Agent (maximum of 6 rounds)
      ├── LLMClient: Anthropic or OpenAI-compatible
      ├── ToolRegistry
      │    ├── catalog and payments
      │    ├── orders and returns
      │    ├── policies, store information, hours, and handoff
      │    └── typed CSV data
      └── SessionMemory (JSON)
```

The model interprets the user message and selects tools. Prices, stock, discounts, installments, shipping, authentication, and deadlines are calculated in Python.

## Technical decisions

- **Hybrid function calling:** the domain is small and closed, so typed tools are safer than text-to-SQL.
- **`Decimal`:** monetary values never use `float`.
- **Lexical policy retrieval:** the manual is short and has stable sections, so deterministic keyword retrieval is easier to test. Embeddings would be more appropriate for a much larger manual.
- **JSON memory:** sufficient for local sessions and demonstrations; history is bounded by turns.
- **Providers:** Anthropic and OpenAI-compatible adapters allow changing providers through environment variables.

## Data rules

- `coming_soon`, discontinued, and out-of-stock products are not offered.
- Only active promotions are used; promotions do not stack and the highest discount wins.
- Inconsistent descriptions are not used to override product names and specifications.
- PIX applies a 5% discount only when the items are not on promotion.
- In Campo Grande, shipping is free only above R$ 500.00; orders up to and including R$ 500.00 cost R$ 35.00.
- Order lookup requires the order number and phone, or a unique email. After three failed attempts in a session, lookup is blocked.
- Address, phone, email, and opening hours are returned by the store-information tool.
- Estimated delivery is used as a receipt-date proxy because the CSVs do not contain the actual receipt date.
- Reproducible frozen-clock scenarios use `EMPORIO_NOW=2026-03-01T10:00:00-04:00`.

Data inconsistencies are recorded in memory through `DataStore.audits`; they are not silently corrected.

### Known contradictions

- The manual contains two phone numbers; the flow uses the cover phone, `(67) 3341-4444`, and does not invent a WhatsApp number.
- The manual contains email variations; the flow uses `contato@emporiodamusica.com.br`.
- The general rule mentions a R$ 100.00 minimum installment, but the more specific tiered section prevails: R$ 50.00 up to 3 installments, R$ 80.00 from 4 to 6, and R$ 100.00 from 7 to 12.
- The manual describes a 30-day defect exchange and a 90-day legal warranty; the agent explains both layers.
- The manual mentions more than 300 instruments, while the CSV contains 65 products; the CSV is the source for catalog answers.

## Privacy and security

- Order data is returned only after identity validation.
- Authentication errors are intentionally generic.
- `--debug` shows tool names, not credentials or private payloads.
- Keys must remain in environment variables and must never be committed.

## Tests and scenarios

Unit tests cover catalog search, promotions, payments, shipping, authentication, returns, store hours, memory, and the tool loop:

```text
uv run --with pytest pytest
21 passed
```

Demonstration scenarios are listed in [`examples/scenarios.json`](examples/scenarios.json). Three real Gemini conversations are stored in [`examples/`](examples/), with a consolidated index in [`examples/real-conversations.json`](examples/real-conversations.json).

## Known limitations

- Shipping outside the metropolitan region is not actually quoted by ZIP code.
- Holidays are not checked.
- There is no live WhatsApp, email, or support-dashboard integration.
- Handoff records exist only during the local process.
- Final response quality still depends on the configured model.

## Use of AI assistants

AI assistants were used to accelerate data inspection, propose the initial module separation, and review test cases. The implementation, business rules, data decisions, and test execution were reviewed in the repository. No key or external private data was included in the codebase.
