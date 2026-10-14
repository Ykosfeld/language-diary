# Diário de Prática de Idiomas com IA

Aplicativo desktop minimalista em formato de diário focado no aprendizado e retenção de idiomas (*Language Agnostic*, foco inicial em Alemão e Inglês).

## Princípios Pedagógicos

1. **O Diário (Escrita):** Ambiente minimalista imitando tinta no papel, sem correções em tempo real, contadores ou distrações, preservando o fluxo cognitivo.
2. **A Mesa do Professor (Análise):** Ambiente desacoplado para revisão longitudinal, relatórios gerados por LLM e visualização detalhada de páginas passadas.
3. **Preservação do Original:** O texto bruto (`raw_text`) permanece intocado e imutável no SQLite; anotações e correções coexistem em camadas analíticas.

## Estrutura do Projeto

```text
language-diary/
├── config.yaml          # Configurações do usuário, tema e pipelines
├── data/                # Banco de dados SQLite local (diary.db)
└── src/
    ├── main.py          # Entrypoint da aplicação
    ├── core/            # Configuração, banco de dados e controle de imutabilidade
    ├── nlp/             # Pipeline GEC, alinhamento e anotações morfossintáticas
    ├── llm/             # Retrieval de erros, relatórios longitudinais e cliente Ollama/APIs
    └── ui/              # Interfaces PyQt6/PySide6 (Diário, Dashboard, Red Pen)
```

## Fases de Desenvolvimento

- [ ] **Fase 1:** Interface de Escrita (O Diário) e Persistência Base (SQLite & Imutabilidade)
- [ ] **Fase 2:** Motor Analítico Diário (GEC Local + spaCy Universal Dependencies)
- [ ] **Fase 3:** A "Mesa do Professor" (Dashboard Semanal e Visualizador Micro)
- [ ] **Fase 4:** Memória Longitudinal e RAG Estruturado
