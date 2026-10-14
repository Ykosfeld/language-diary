# Roadmap do Projeto: Diário de Prática de Idiomas com IA (v4)

## 1. Contexto para LLMs Futuros

- **Objetivo deste Documento:** Fornecer contexto arquitetural, contratos de dados e estado atual do projeto para que instâncias de LLM auxiliem na implementação mantendo consistência de código.
- **Perfil do Desenvolvedor:** Yuri, graduando em Matemática, usuário de Linux (Fedora/KDE). Experiência com Python, C, pipelines de dados, Machine Learning (PyTorch, Transformers, sistemas de retrieval) e infraestrutura em home lab (Fedora Server).
- **Visão do Projeto:** Aplicativo desktop em formato de diário focado no aprendizado de idiomas (arquitetura *Language Agnostic*, com foco inicial em **Alemão** e **Inglês**).
- **Premissa Pedagógica (Fricção Zero e Separação de Ambientes):**
  1. **O Diário (Escrita):** Ambiente minimalista imitando tinta no papel, sem correções em tempo real, sublinhados ou distrações, preservando a fluidez cognitiva.
  2. **A Mesa do Professor (Análise):** Ambiente separado para feedback longitudinal (relatórios semanais via LLM) e revisão detalhada de páginas passadas já fechadas.
- **Topologia de Execução (MVP):** Execução 100% local no Desktop (interface, banco SQLite e inferência de modelos NLP/LLM locais), mantendo desacoplamento entre UI e serviços para permitir migração futura do backend para o Fedora Server.

---

## 2. Regras Arquiteturais (Guardrails para LLMs)

1. **Zero Feedback na Janela de Escrita:** NUNCA adicione spellcheckers, contadores de erro, sublinhados ou chamadas visíveis de IA na tela do Diário (Fase 1).
2. **Desacoplamento UI-Core:** Código de interface (`PyQt6`/`PySide6`) não deve conter queries SQL ou chamadas diretas ao PyTorch/Ollama. Use a camada de serviços e `QThread`/`QRunnable` para não travar a interface gráfica.
3. **Preservação do Texto Original:** O texto bruto escrito pelo usuário (`raw_text`) jamais deve ser sobrescrito pelo texto anotado (`annotated_text`). Ambos coexistem no banco para permitir reprocessamento futuro caso o motor de NLP seja atualizado.
4. **Extensibilidade de Idiomas:** Regras gramaticais não devem ser *hardcoded* no fluxo principal. Utilize o padrão *Strategy* por idioma apoiado em tags morfossintáticas universais (*Universal Dependencies*).

---

## 3. Estrutura de Diretórios Planejada

```text
language-diary/
├── config.yaml                 # Configurações do usuário e de idiomas
├── data/
│   └── diary.db                # Banco de dados SQLite local
├── src/
│   ├── main.py                 # Entrypoint da aplicação
│   ├── core/
│   │   ├── config.py           # Loader e validação do config.yaml
│   │   ├── database.py         # Conexão SQLite, migrations e repositórios
│   │   └── lock_manager.py     # Lógica de imutabilidade (midnight vs on_submit)
│   ├── nlp/                    # Fase 2: Motor Analítico Diário
│   │   ├── base_engine.py      # Interface abstrata (Language Agnostic)
│   │   ├── corrector.py        # Modelo GEC local (Seq2Seq / GECToR / LanguageTool)
│   │   ├── aligner.py          # Diff de tokens + Classificação via spaCy (UD)
│   │   └── xml_serializer.py   # Conversor de spans de erro para tags <err> e HTML
│   ├── llm/                    # Fases 3 e 4: Relatórios e RAG
│   │   ├── retriever.py        # Queries estruturadas de erros recorrentes no SQLite
│   │   ├── prompt_builder.py   # Montagem do prompt longitudinal
│   │   └── client.py           # Cliente para Ollama local ou API externa
│   └── ui/                     # Interfaces PyQt6 / PySide6
│       ├── writer_window.py    # Fase 1: O Diário (Minimalista)
│       ├── dashboard_window.py # Fase 3: A Mesa do Professor (Visão Macro)
│       └── red_pen_view.py     # Fase 3: Visualizador de "Rabiscos do Professor" (Visão Micro)
```

---

## 4. Contratos de Dados e Especificações

### 4.1. Configuração (`config.yaml`)

```yaml
user:
  native_language: "pt-BR"
  active_target_language: "de" # Idioma atual (ex: "de", "en")

diary:
  lock_policy: "daily_midnight" # Opções: "daily_midnight" (1 pág/dia, trava à 00:00) | "on_submit" (trava ao clicar em finalizar)
  theme: "sepia"                # Opções: "sepia", "solarized_light", "paper_dark"
  font_family: "Noto Serif"
  font_size: 14

nlp:
  run_on_lock: true             # Dispara a Fase 2 automaticamente em background assim que a entrada é travada
  llm_provider: "ollama"        # Opções: "ollama", "openai", "anthropic", "gemini"
  llm_model: "llama3.1:8b"
```

### 4.2. Especificação da Tag de Anotação In-line (`<err>`)

Todas as anotações geradas na Fase 2 seguem o contrato XML abaixo dentro de `annotated_text`:

- **Substituição (1:1 ou N:M):** `Ich gehe in <err type="declination" expected="den">das</err> Park.`
- **Omissão (Palavra faltando — tag com corpo vazio):** `Ich warte <err type="preposition_missing" expected="auf"></err> den Bus.`
- **Inserção Indevida (Palavra sobrando — `expected` vazio):** `Ich habe <err type="unnecessary_word" expected="">zu</err> gearbeitet.`
- **Ordem de Palavras (Word Order — engloba o sintagma afetado):** `..., weil ich <err type="word_order" expected="müde bin">bin müde</err>.`

**Categorias base de `type` (extensíveis via Universal Dependencies):** `declination` (caso/gênero), `conjugation` (tempo/pessoa verbal), `word_order`, `preposition`, `orthography` (inclui capitalização de substantivos no alemão), `lexical_choice`, `missing_word`, `unnecessary_word`.

### 4.3. Esquema do Banco de Dados (SQLite DDL)

```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL,            -- Formato YYYY-MM-DD
    target_language TEXT NOT NULL,       -- Ex: 'de', 'en'
    status TEXT NOT NULL DEFAULT 'DRAFT',-- 'DRAFT' | 'LOCKED' | 'ANALYZED'
    raw_text TEXT NOT NULL,              -- Texto original imutável do usuário
    annotated_text TEXT,                 -- Texto com tags <err ...> gerado na Fase 2
    word_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMP
);

-- Tabela desnormalizada de erros para facilitar agregações estatísticas e RAG (Fase 4)
CREATE TABLE error_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    target_language TEXT NOT NULL,
    error_type TEXT NOT NULL,            -- Ex: 'declination', 'word_order'
    original_span TEXT,                  -- Ex: 'das'
    expected_span TEXT,                  -- Ex: 'den'
    sentence_context TEXT NOT NULL,      -- Frase completa onde o erro ocorreu
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE weekly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_language TEXT NOT NULL,
    period_start TEXT NOT NULL,          -- YYYY-MM-DD
    period_end TEXT NOT NULL,            -- YYYY-MM-DD
    report_markdown TEXT NOT NULL,       -- Feedback qualitativo gerado pelo LLM
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_entries_date_lang ON entries(entry_date, target_language);
CREATE INDEX idx_errors_lang_type ON error_logs(target_language, error_type);
```

---

## 5. Fases de Implementação e Status

**Fase Atual de Desenvolvimento:** Fase 1 (MVP da Interface e Persistência)

### Fase 1: Interface de Escrita (O Diário) e Persistência Base

- [ ] **Setup do Projeto e Banco:** Criar estrutura de diretórios, loader do `config.yaml` e inicialização do SQLite (`entries`, `error_logs`, `weekly_reports`).
- [ ] **Design Minimalista (`PyQt6`/`PySide6`):** Janela limpa com estética de papel (Sépia/Solarized Light), tipografia serifada, cabeçalho discreto exibindo a data e seletor de idioma ativo.
- [ ] **Gerenciador de Imutabilidade ("Tinta no Papel"):**
      - Modo `daily_midnight`: Permite editar a página do dia atual (`status = 'DRAFT'`) com auto-save; na inicialização do app (ou virada de data), trava automaticamente páginas de dias anteriores (`status = 'LOCKED'`).
      - Modo `on_submit`: Botão "Finalizar Página" que trava imediatamente a entrada atual e permite abrir novas entradas no mesmo dia.

### Fase 2: O Motor Analítico Diário (NLP Local e In-line Annotation)

- [ ] **Worker Assíncrono:** Fila em background (`QThread`) que processa entradas recém-travadas (`LOCKED` -> `ANALYZED`) sem bloquear a UI.
- [ ] **Pipeline GEC + Alinhamento Universal Dependencies:**
      - *Passo 1 (Correção):* Geração da versão corrigida frase a frase via modelo local leve (Seq2Seq GEC para Alemão/Inglês ou integração com LanguageTool local).
      - *Passo 2 (Alinhamento e Tipagem):* Comparação entre frase original e corrigida usando `spaCy` (`de_core_news_md` / `en_core_web_md`) para extrair mudanças morfossintáticas (`Case`, `Gender`, `VerbForm`, `WordOrder`) e classificar o `type` de forma agnóstica de idioma.
- [ ] **Serialização e Persistência:** Injetar as tags `<err>` gerando o `annotated_text` na tabela `entries` e popular os registros individuais na tabela `error_logs`.

### Fase 3: A "Mesa do Professor" (Dashboard Semanal, LLM e Folha Corrigida)

- [ ] **Janela Separada (Dashboard):** Interface dedicada para estudo e revisão, isolada do ambiente de escrita.
- [ ] **Visão Macro (Feedback Qualitativo em Lote):** Agregador que coleta as entradas `annotated_text` da semana e envia em lote para o LLM (via Ollama local ou API). A leitura direta das tags in-line permite ao LLM gerar um relatório pedagógico encorajador e contextualizado, salvo em `weekly_reports`.
- [ ] **Visão Micro ("Rabiscos do Professor"):** Aba/modal secundário onde o usuário seleciona uma entrada passada já fechada e visualiza o texto com marcações visuais estilo revisão de caderno (renderização HTML/CSS das tags `<err>`: texto original riscado, correção esperada destacada e tooltip com o tipo gramatical).

### Fase 4: Memória de Longo Prazo e RAG Longitudinal

- [ ] **Retrieval Estruturado (`error_logs`):** Consultas SQL analíticas que identificam os *top N* tipos de erro mais frequentes nas últimas semanas, variações de taxa de erro por 100 palavras e exemplos de frases anteriores com a mesma falha.
- [ ] **Injeção de Contexto Longitudinal:** Enriquecimento automático do prompt da Fase 3 com o histórico recuperado (ex: *"Nas últimas 3 semanas, o aluno reduziu erros de `word_order` em orações subordinadas em 40%, mas ainda persiste a troca entre Acusativo e Dativo após preposições de movimento"*), permitindo que o "professor" reconheça evoluções e foque nos pontos cegos reais.
