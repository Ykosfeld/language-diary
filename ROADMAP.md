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
│   ├── nlp/                    # Fase 2: Motor Analítico Diário (Híbrido: LT + LLM)
│   │   ├── base_engine.py      # Interface abstrata do motor analítico
│   │   ├── languagetool_client.py # Filtro Mecânico: Cliente HTTP local (LanguageTool Server)
│   │   ├── llm_syntax_judge.py # Juiz Sintático: Ollama JSON focado em Word Order & Sintaxe
│   │   ├── normalizer.py       # Extração de word_target e normalização de termos
│   │   └── annotator.py        # Mesclador e serializador posicional de tags <err>
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

-- Tabela analítica de erros para agregações estatísticas, dashboard e RAG (Fases 3 e 4)
CREATE TABLE error_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    target_language TEXT NOT NULL,       -- Ex: 'de', 'en'
    
    -- Categorização do erro (baseada no LanguageTool / taxonomia universal)
    category TEXT NOT NULL,              -- Macro-categoria: 'GRAMMAR', 'TYPOS', 'CASING', 'SYNTAX'
    rule_id TEXT NOT NULL,               -- Regra específica: 'DE_AGREEMENT', 'GERMAN_SPELLER_RULE', 'NON3PRS_VERB'
    rule_description TEXT,               -- Descrição amigável da regra violada
    message TEXT,                        -- Mensagem pedagógica explicativa
    
    -- Spans contextuais
    original_span TEXT NOT NULL,         -- Trecho original incorreto (ex: 'das Park', 'muede')
    expected_span TEXT,                  -- Correção prioritária recomendada (ex: 'den Park', 'müde')
    sentence_context TEXT NOT NULL,      -- Frase completa onde o erro ocorreu (para estudo/RAG)
    
    -- Campo analítico normalizado para ranking de vocabulário problemático ("qual palavra mais erro?")
    word_target TEXT,                    -- Palavra-alvo correta normalizada/minúscula (ex: 'park', 'müde', 'go')
    
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
CREATE INDEX idx_errors_lang_rule ON error_logs(target_language, rule_id);
CREATE INDEX idx_errors_word_target ON error_logs(target_language, word_target);
CREATE INDEX idx_errors_entry_id ON error_logs(entry_id);
```

---

## 5. Fases de Implementação e Status

**Fase Atual de Desenvolvimento:** Fase 1 (MVP da Interface e Persistência)

### Fase 1: Interface de Escrita (O Diário) e Persistência Base

- [x] **Setup do Projeto e Banco:** Criar estrutura de diretórios, loader do `config.yaml` e inicialização do SQLite (`entries`, `error_logs`, `weekly_reports`).
- [x] **Design Minimalista (`PyQt6`/`PySide6`):** Janela limpa com estética de papel (Sépia/Solarized Light), tipografia serifada, cabeçalho discreto exibindo a data e seletor de idioma ativo.
- [x] **Gerenciador de Imutabilidade ("Tinta no Papel"):**
      - Modo `daily_midnight`: Permite editar a página do dia atual (`status = 'DRAFT'`) com auto-save; na inicialização do app (ou virada de data), trava automaticamente páginas de dias anteriores (`status = 'LOCKED'`).
      - Modo `on_submit`: Botão "Finalizar Página" que trava imediatamente a entrada atual e permite abrir novas entradas no mesmo dia.

### Fase 2: O Motor Analítico Diário (Pipeline Híbrido: LanguageTool + LLM Sintático)

- [ ] **Worker Assíncrono:** Fila em background (`QThread`) que processa entradas recém-travadas (`LOCKED` -> `ANALYZED`) sem bloquear a UI.
- [ ] **Arquitetura em Duas Etapas (Cascade / Staged Pipeline):**
      - *Etapa 1 (Filtro Mecânico - LanguageTool Local):*
        - Envio de `raw_text` para o LanguageTool HTTP Server (`/v2/check`).
        - Filtro ultra-rápido (<50ms) e determinístico para erros ortográficos (`TYPOS`), capitalização de substantivos (`CASING`) e concordâncias imediatas de gênero/número/caso (`DE_AGREEMENT`).
        - Gera a lista de spans mecânicos com `offset` e `length` e produz um `clean_text` temporário (com as correções locais aplicadas).
      - *Etapa 2 (Juiz Sintático Especializado - Ollama LLM):*
        - Envio do `clean_text` para o LLM local (`llama3.1:8b` via Ollama) com prompt cirúrgico e saída estritamente em JSON (`format: "json"`).
        - *Guardrails de Prompt (Negative Constraints):* O LLM é expressamente proibido de corrigir erros de digitação, pontuação trivial ou reescrever frases por questões de "estilo/beleza". Seu foco é exclusivo em desvios estruturais graves que o LanguageTool não cobre:
          1. *Word Order:* Posição do verbo conjugado em orações subordinadas (*Nebensätze* com *weil/dass/obwohl*), posição do particípio no *Perfekt*, regra V2 em orações principais.
          2. *Regência Verbal e Preposições:* Preposição obrigatória omitida ou incorreta exigida pelo verbo.
      - *Etapa 3 (Mesclagem, Resolução de Sobreposição e Persistência):*
        - *No SQLite (`error_logs`):* Todos os erros detectados por ambos os motores são registrados individualmente com seus respectivos metadados (`category`, `rule_id`, `message`, `word_target`).
        - *No Texto Anotado (`annotated_text`):* O `annotator.py` reconcilia os spans. Em caso de colisão (ex: um erro de digitação local que ocorre dentro de uma oração subordinada com erro de *Word Order*), a anotação visual prioriza a tag estrutural macro (`word_order`), preservando a clareza e evitando poluição visual nas marcações. Extrai-se o `word_target` normalizado para alimentar as métricas do banco.

### Fase 3: A "Mesa do Professor" (Dashboard Semanal, LLM e Folha Corrigida)

- [ ] **Janela Separada (Dashboard):** Interface dedicada para estudo e revisão, isolada do ambiente de escrita.
- [ ] **Visão Macro (Dashboard Estatístico e Feedback em Lote):**
      - *Cards Analíticos:* Métricas agregadas via SQLite com:
        - **Top Regras Violadas:** Ranking das infrações gramaticais mais frequentes (`rule_id` / `category`).
        - **Palavras Traiçoeiras:** Ranking das palavras mais frequentemente erradas (`word_target`) com histórico de como foram escritas vs forma correta.
        - **Evolução Longitudinal:** Gráfico de linha da taxa de erros normalizada a cada 100 palavras ao longo das semanas.
      - *Feedback Qualitativo:* Agregador que envia o resumo estatístico e amostras de frases para o LLM local (Ollama `llama3.1:8b`) para gerar um relatório pedagógico encorajador salvo em `weekly_reports`.
- [ ] **Visão Micro ("Rabiscos do Professor"):** Aba/modal secundário onde o usuário seleciona uma entrada passada já fechada e visualiza o texto com marcações visuais estilo revisão de caderno (renderização HTML/CSS das tags `<err>`: texto original riscado, correção esperada destacada e tooltip com a explicação pedagógica).

### Fase 4: Memória de Longo Prazo e RAG Longitudinal

- [ ] **Retrieval Estruturado (`error_logs`):** Consultas SQL analíticas que identificam os *top N* tipos de erro mais frequentes nas últimas semanas, variações de taxa de erro por 100 palavras e histórico de palavras reincidentes em `word_target`.
- [ ] **Injeção de Contexto Longitudinal:** Enriquecimento automático do prompt da Fase 3 com o histórico recuperado (ex: *"Nas últimas semanas, o aluno eliminou erros de capitalização de substantivos, mas ainda persiste na confusão de gênero para a palavra 'Park' e erros com preposições acusativas"*), permitindo que o "professor" reconheça evoluções e foque nos pontos cegos reais.
