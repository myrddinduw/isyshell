# Diagrama de Arquitetura do IsyShell

## Fluxo de Requisição

```mermaid
flowchart TD
    A[Cliente\ncurl / app / browser] -->|HTTP Request\nX-Isy-Token: xyz| B[FastAPI\nmain.py]

    B --> C{auth.py\nToken válido?}
    C -->|NÃO| D[HTTP 401\nNão Autorizado]
    C -->|SIM - Admin| E[Acesso Total]
    C -->|SIM - Usuário| F{Verificações\nde Plano}

    F -->|Plano insuficiente| G[HTTP 403 Proibido]
    F -->|Limite diário atingido| H[HTTP 429 Rate Limit]
    F -->|OK| E

    E -->|GET /scripts| I[database.py\nSELECT scripts]
    E -->|POST /scripts| I
    E -->|POST /scripts/n/executar| J[executor.py]
    E -->|GET /logs| I
    E -->|PUT /config/token| I
    E -->|GET /analytics/*| K[analytics.py\nMétricas SQL]
    E -->|POST /usuarios/*| L[users.py\nCadastro e Login]

    J --> M{Script ativo\nno banco?}
    M -->|NÃO| N[Erro: não encontrado]
    M -->|SIM| O{Parâmetros\nseguros?}

    O -->|NÃO| P[Erro: parâmetro perigoso]
    O -->|SIM| Q[subprocess.run\nsem shell=True\ncomo lista\n+ time.time]

    Q --> R[scripts/\npasta com .sh\nmontada via Volume]
    Q --> S[Resultado\nstdout + stderr\n+ duracao_segundos]

    S --> T[database.py\nINSERT execucoes\nusuario_id + duracao]
    T --> U[JSON de resposta]

    I --> U
    K --> U
    L --> U
    U --> A
```

---

## Componentes e Responsabilidades

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CONTAINER DOCKER                             │
│                                                                        │
│  ┌─────────────┐    ┌───────────┐    ┌─────────────────────────┐     │
│  │   main.py   │───▶│  auth.py  │    │      executor.py        │     │
│  │  (roteador) │    │(porteiro) │    │  • Valida parâmetros    │     │
│  └──────┬──────┘    └───────────┘    │  • subprocess como lista│     │
│         │                            │  • Sem shell=True       │     │
│         │           ┌───────────┐    │  • Mede duracao_segundos│     │
│         ├──────────▶│schemas.py │    └──────────┬──────────────┘     │
│         │           │ (moldes)  │               │                     │
│         │           └───────────┘               ▼                     │
│         │                            ┌────────────────────┐           │
│         │           ┌───────────┐    │  /scripts/ VOLUME  │           │
│         ├──────────▶│ users.py  │    │  limpar_logs.sh    │           │
│         │           │(freemium) │    │  checar_docker.sh  │           │
│         │           └───────────┘    └────────────────────┘           │
│         │                                                              │
│         │           ┌───────────┐                                      │
│         ├──────────▶│analytics.py│                                     │
│         │           │(métricas) │                                      │
│         │           └───────────┘                                      │
│         │                                                              │
│         │           ┌───────────┐                                      │
│         └──────────▶│payments.py│◀── POST /webhooks/stripe             │
│                     │ (Stripe)  │        (Stripe envia aqui)           │
│                     └───────────┘                                      │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                  database.py — SQLite                         │     │
│  │  ┌──────────┐  ┌────────────────────────┐  ┌─────────────┐  │     │
│  │  │ scripts  │  │       execucoes         │  │ configuracoes│  │     │
│  │  │(cadastro)│  │ usuario_id, duracao_seg │  │(token admin)│  │     │
│  │  │plano_min │  │ stdout, stderr, status  │  └─────────────┘  │     │
│  │  └──────────┘  └────────────────────────┘                    │     │
│  │  ┌──────────────────────────────────────┐                    │     │
│  │  │              usuarios                │                    │     │
│  │  │  email, senha_hash, plano, token     │                    │     │
│  │  └──────────────────────────────────────┘                    │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                          /app/data/isyshell.db                         │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                               HOST (sua máquina)
                               ./data/isyshell.db  (persistido)
                               ./scripts/*.sh      (editável sem rebuild)
```
