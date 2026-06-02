# Diagrama de Arquitetura do IsyShell

## Fluxo de Requisição

```mermaid
flowchart TD
    A[Cliente\ncurl / app / browser] -->|HTTP Request\nX-Isy-Token: xyz| B[FastAPI\nmain.py]

    B --> C{auth.py\nToken válido?}
    C -->|NÃO| D[HTTP 401\nNão Autorizado]
    C -->|SIM| E[Rota solicitada]

    E -->|GET /scripts| F[database.py\nSELECT scripts]
    E -->|POST /scripts| F
    E -->|POST /scripts/n/executar| G[executor.py]
    E -->|GET /logs| F
    E -->|PUT /config/token| F

    G --> H{Script ativo\nno banco?}
    H -->|NÃO| I[Erro: não encontrado]
    H -->|SIM| J{Parâmetros\nseguros?}

    J -->|NÃO| K[Erro: parâmetro perigoso]
    J -->|SIM| L[subprocess.run\n sem shell=True\ncomo lista]

    L --> M[scripts/\npasta com .sh\nmontada via Volume]
    L --> N[Resultado\nstdout + stderr]

    N --> O[database.py\nINSERT execucoes\nauditoria]
    N --> P{Falhou?}
    P -->|SIM| Q[alerts.py\nWebhook Discord]
    P -->|NÃO| R[JSON de sucesso]
    Q --> R

    F --> R
    O --> R
    R --> A
```

## Componentes e Responsabilidades

```
┌─────────────────────────────────────────────────────────────────┐
│                        CONTAINER DOCKER                          │
│                                                                   │
│  ┌─────────────┐    ┌──────────┐    ┌──────────────────────┐    │
│  │   main.py   │───▶│  auth.py │    │     executor.py      │    │
│  │  (roteador) │    │ (porteiro)│    │  (operário seguro)   │    │
│  └──────┬──────┘    └──────────┘    │  • Valida parâmetros │    │
│         │                           │  • subprocess lista  │    │
│         │           ┌──────────┐    │  • Sem shell=True    │    │
│         ├──────────▶│schemas.py│    └──────────┬───────────┘    │
│         │           │(moldes)  │               │                │
│         │           └──────────┘               ▼                │
│         │                           ┌─────────────────────┐     │
│         │           ┌──────────┐    │   /scripts/ VOLUME  │     │
│         ├──────────▶│ alerts.py│    │   limpar_logs.sh    │     │
│         │           │(Discord) │    │   checar_docker.sh  │     │
│         │           └──────────┘    └─────────────────────┘     │
│         │                                                         │
│         ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              database.py — SQLite                        │    │
│  │  ┌──────────┐  ┌─────────────┐  ┌──────────────────┐   │    │
│  │  │ scripts  │  │  execucoes  │  │  configuracoes   │   │    │
│  │  │(cadastro)│  │ (auditoria) │  │  (token, etc.)   │   │    │
│  │  └──────────┘  └─────────────┘  └──────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                /app/data/isyshell.db             │
└─────────────────────────────────────────────────────────────────┘
                                         │
                                    HOST (sua máquina)
                                    ./data/isyshell.db  (persistido)
                                    ./scripts/*.sh      (editável)
```
