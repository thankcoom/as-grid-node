# File Structure & Organization Guide

This document maps out the `bitget_as` codebase to help you find what you need.

## Top-Level Directories

| Directory | Purpose |
| :--- | :--- |
| **`auth_server/`** | The Backend API. Handles Users, Auth, Database, and "Manager" logic. |
| **`saas_frontend/`** | The User Interface. The Website users see. |
| **`grid_node/`** | The Trading Bot logic. This is where the actual trading code lives. |
| **`documentation/`** | Project docs (You are here). |
| **`deploy/`** | Deployment scripts (Docker, K8s, etc.). |

---

## Detailed Breakdown

### 🖥️ `saas_frontend/` (React)
- `src/`
    - `pages/`: Full page views (e.g., `Login.jsx`, `Dashboard.jsx`).
    - `components/`: Reusable UI chunks (e.g., `Navbar.jsx`, `Icons.jsx`).
    - `services/`: API wrappers (e.g., `api.js` connects to backend).
    - `context/`: Global state (e.g., `AuthContext.jsx` stores the User Token).

### ⚙️ `auth_server/` (FastAPI)
- `app/`
    - `main.py`: The entry point. Starts the server.
    - `api/`: API Route definitions (e.g., `auth.py`, `grid.py`).
    - `core/`: Config settings (Database URL, Secret Keys).
    - `models/`: Database Schema definitions (User table, Orders table).
    - `services/`: Business logic (e.g., `bitget_service.py` to check UIDs).

### 🤖 `grid_node/` (Python)
- `app/`
    - `main.py`: Entry point for the bot process.
    - `strategies/`: Different trading algorithms.
    - `bitget_client.py`: Low-level wrapper for Bitget API calls.

### 📄 Key Root Files
- `docker-compose.yml`: Defines how to run the whole stack locally (Frontend + Backend + DB).
- `saas計畫.md`: The original masterplan (Legacy/Reference).
