# Agente de atendimento — Empório da Música

Agente de atendimento em Python para catálogo, preços, pedidos, políticas e encaminhamento humano.

## Rodando

Requer Python 3.11+ e [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
Copy-Item .env.example .env
# preencha EMPORIO_API_KEY no ambiente ou no .env
uv run emporio-agent
```

O comando aceita:

```text
--data        diretório dos CSVs
--session     nome da sessão persistida
--memory-dir  diretório dos JSONs de sessão
--debug       mostra nomes das ferramentas chamadas
```

O CLI não carrega `.env` automaticamente. No PowerShell, carregue a variável antes de iniciar:

```powershell
$env:EMPORIO_API_KEY = "sua-chave"
uv run emporio-agent --debug
```

Para validar sem provedor externo:

```powershell
uv run --with pytest pytest
```

## Arquitetura

```text
CLI
 └── Agent (máximo de 6 rodadas)
      ├── LLMClient: Anthropic ou OpenAI-compatível
      ├── ToolRegistry
      │    ├── catálogo e pagamentos
      │    ├── pedidos e trocas
      │    ├── políticas, dados da loja, horário e handoff
      │    └── dados tipados dos CSVs
      └── SessionMemory (JSON)
```

O modelo interpreta a mensagem e escolhe ferramentas. Preço, estoque, desconto, parcelas, frete, autenticação e prazos são calculados em Python.

## Decisões

- **Function calling híbrido:** o domínio é pequeno e fechado, então ferramentas tipadas são mais seguras que text-to-SQL.
- **`Decimal`:** valores monetários não usam `float`.
- **Políticas lexicais:** o manual é curto e tem seções estáveis; busca por termos é determinística e testável. Embeddings fariam mais sentido para um manual muito maior.
- **Memória JSON:** suficiente para sessões locais e demonstração; o histórico é limitado por turnos.
- **Provedores:** o adaptador Anthropic e o adaptador OpenAI-compatível permitem trocar o fornecedor por ambiente.

## Regras de dados

- Produtos `coming_soon`, descontinuados ou sem estoque não são ofertados.
- Só promoções ativas são usadas; promoções não acumulam e prevalece o maior desconto.
- Descrições inconsistentes não são usadas para substituir nome e especificações.
- PIX aplica 5% somente quando os itens não estão em promoção.
- Em Campo Grande, frete é grátis somente acima de R$ 500,00; até R$ 500,00 custa R$ 35,00.
- Consulta de pedido exige número e telefone, ou e-mail quando único. Após três falhas na sessão, a consulta é bloqueada.
- Endereço, telefone, e-mail e horário são retornados pela ferramenta de dados da loja.
- A data de entrega é usada como proxy da data de recebimento porque os CSVs não têm data efetiva de recebimento.
- Para reproduzir cenários com relógio congelado, use `EMPORIO_NOW=2026-03-01T10:00:00-04:00`.

As inconsistências são auditadas em memória por `DataStore.audits`; não são corrigidas silenciosamente.

### Contradições conhecidas

- O manual apresenta dois telefones; o fluxo usa o telefone principal da capa, `(67) 3341-4444`, e não inventa um WhatsApp.
- O manual apresenta variações de e-mail; o fluxo usa `contato@emporiodamusica.com.br`.
- A regra geral menciona parcela mínima de R$ 100,00, mas a seção específica por faixa prevalece: R$ 50,00 até 3x, R$ 80,00 de 4x a 6x e R$ 100,00 de 7x a 12x.
- O manual traz troca por defeito em 30 dias e garantia legal de 90 dias; o agente explica as duas camadas.
- O manual menciona mais de 300 instrumentos, enquanto o CSV contém 65 produtos; o catálogo consultável é sempre o CSV.

## Privacidade e segurança

- Dados do pedido só são retornados depois da validação.
- Mensagens de erro de autenticação são genéricas.
- O modo `--debug` exibe nomes de ferramentas, não conteúdo de credenciais.
- Chaves devem permanecer em variáveis de ambiente e nunca ser commitadas.

## Testes e cenários

Os testes unitários cobrem catálogo, promoções, pagamentos, frete, autenticação, troca, horário, memória e laço de ferramentas:

```text
uv run --with pytest pytest
21 passed
```

Os cenários de demonstração estão em [`examples/scenarios.json`](examples/scenarios.json). As três conversas reais executadas com Gemini estão em [`examples/`](examples/), com o índice consolidado em [`examples/real-conversations.json`](examples/real-conversations.json).

## Limitações conhecidas

- Frete fora da região metropolitana não é cotado de verdade por CEP.
- Feriados não são consultados.
- Não existe integração real com WhatsApp, e-mail ou painel de atendimento.
- O retorno do handoff é registrado apenas durante o processo local.
- A qualidade da resposta final ainda depende do modelo configurado.

## Uso de assistentes de IA

Assistentes foram usados para acelerar a inspeção dos dados, propor a separação inicial de módulos e revisar casos de teste. A implementação, as regras de negócio, as decisões sobre inconsistências e a execução dos testes foram revisadas no repositório. Nenhuma chave ou dado externo foi incluído no código.
