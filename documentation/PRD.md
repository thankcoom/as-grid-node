# Product Requirements Document (PRD) - Bitget AS Grid SaaS

## 1. Introduction
**Project Name**: Bitget AS Grid Trading System
**Goal**: Build a secure, scalable SaaS platform that allows users to run automated "AS Grid" trading strategies on their own Bitget accounts via API binding.
**Key Features**:
- **Invite-only Registration**: Whitelisted UID verification.
- **User Isolation**: Each user's trading logic runs in a separate process/container.
- **Non-Custodial**: Users keep their funds on Bitget; the system only trades via API.

## 2. User Flows

### 2.1 Registration & Onboarding
1.  **User Visits Site**: Inputs Email + Password (No invite code required).
2.  **API Binding**: User inputs Bitget API Key, Secret, and Passphrase.
3.  **Validation**:
    - System calls Bitget API to fetch the user's UID.
    - System checks UID against an internal "Whitelist Database".
    - **Match**: Account Status -> `Active`.
    - **No Match**: Account Status -> `Pending Approval` or `Rejected`.

### 2.2 Dashboard & Trading
1.  **Login**: User logs in securely (JWT Auth).
2.  **Configuration**: User sets trading parameters:
    - Trading Pair (e.g., BTC/USDT)
    - Price Range (Lower/Upper)
    - Grid Count
    - Investment Amount
3.  **Start Bot**: User clicks "Start". System spins up a dedicated `Celery` task or Docker container for that user.
4.  **Monitoring**: Dashboard shows real-time PnL, open orders, and trade history.

## 3. Functional Requirements

### Frontend (`saas_frontend`)
- [ ] **Landing Page**: Marketing + Login/Register.
- [ ] **Dashboard**: Main control panel.
- [ ] **Settings**: API Key management.
- [ ] **Admin Panel**: For managing the UID whitelist and viewing system status.

### Backend (`auth_server`)
- [ ] **Authentication**: JWT-based auth.
- [ ] **Encryption**: AES-256 storage for API Keys.
- [ ] **Database**: PostgreSQL for users, orders, and configuration.
- [ ] **Bitget Client**: Service to validate keys and fetch specific user data.

### Trading Engine (`grid_node`)
- [ ] **Isolation**: Logic must support concurrent execution for multiple users without cross-talk.
- [ ] **Algorithm**: "AS Grid" logic (details in restricted codebase).
- [ ] **Safety**: Stop-loss mechanisms, API rate limit handling.

## 4. Non-Functional Requirements
- **Security**: API Keys must NEVER be returned to the frontend in plain text.
- **Scalability**: System should handle 100+ concurrent running bots.
- **Reliability**: Auto-restart on crash (handled by Docker/K8s/Cloud Run).

## 5. Success Metrics
- Successful end-to-end trade execution for a whitelisted user.
- Dashboard accurately reflects exchange data with < 5s latency.
- Secure handling of invalid/expired API keys.
