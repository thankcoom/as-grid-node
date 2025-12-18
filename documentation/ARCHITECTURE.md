# System Architecture

## Overview
The system follows a microservices-inspired architecture, separating the User Interface, Authentication/Management, and the actual Trading execution.

```mermaid
graph TD
    User[User Browser] -->|HTTPS| Frontend[SaaS Frontend (React)]
    Frontend -->|REST API| Backend[Auth Server (FastAPI)]
    
    subgraph Data Layer
        DB[(PostgreSQL)]
        Redis[(Redis/Celery Broker)]
    end
    
    Backend -->|Read/Write| DB
    Backend -->|Dispatch Task| Redis
    
    subgraph Execution Layer
        Worker[Grid Node Worker (Python)]
        Worker -->|Pull Task| Redis
        Worker -->|Update Status| DB
    end
    
    Worker -->|Trade execution| Exchange[Bitget Exchange API]
    Backend -->|Verify UID| Exchange
```

## detailed Components

### 1. SaaS Frontend
- **Tech**: React, Vite, TailwindCSS (optional/custom).
- **Role**: Presentation layer.
- **Key Responsibility**:
    - User Authentication (Login/Register).
    - Dashboard visualization (Charts, Tables).
    - API Key input form.

### 2. Auth Server (Backend)
- **Tech**: Python, FastAPI, SQLAlchemy.
- **Role**: The "Brain" of the SaaS.
- **Key Responsibility**:
    - **User Management**: Signup, Login, JWT issuance.
    - **Security**: Encrypts API keys before storing in DB.
    - **Orchestration**: Receives "Start Bot" command and dispatches it to the Grid Node layer.
    - **Proxy**: Fetches status from DB to show to Frontend.

### 3. Grid Node (Execution Engine)
- **Tech**: Python, Celery (or pure loop), CCXT (or custom requests).
- **Role**: The "Muscle".
- **Key Responsibility**:
    - Receives `(User_API_Key, Config)` from Backend.
    - Connects directly to Bitget.
    - Executes the proprietary "AS Grid" strategy.
    - Updates the Database with Order fills and PnL.

## Data Flow: "Start Bot"
1.  Front end sends `POST /api/grid/start` with config.
2.  Backend validates User + Config.
3.  Backend decrypts User's API Key (in memory only).
4.  Backend triggers a Celery Task (or spawns a container) with the decrypted credentials + config.
5.  Grid Node starts running the loop.

## Security Architecture
- **Encryption**: library `cryptography` (Fernet) used for API Secret storage.
- **Isolation**: Each grid instance runs independently.
- **Least Privilege**: Frontend never sees the API Secret.
