# 🚀 Onboarding Guide - How to Run This Project

Welcome to the team! Follow these steps to get the **Bitget AS Grid** system running on your local machine.

## Prerequisites

- **Docker & Docker Compose**: [Install here](https://docs.docker.com/get-docker/)
- **Node.js**: v16+ (for Frontend)
- **Python**: 3.10+ (for Backend)

## ⚡ Quick Start (The "I just want to run it" way)

We have a `docker-compose.yml` file that spins up everything (Database, Backend, Frontend).

1.  **Clone the repo** (if you haven't).
    ```bash
    git clone <repo_url>
    cd bitget_as
    ```

2.  **Run with Docker Compose**:
    ```bash
    docker-compose up --build
    ```

3.  **Access the App**:
    - Frontend: [http://localhost:3000](http://localhost:3000)
    - Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 💻 Manual Setup (For Development)

If you want to edit code, you should run services locally.

### 1. Backend Setup (`auth_server`)

```bash
cd auth_server
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Server
uvicorn app.main:app --reload
```

### 2. Frontend Setup (`saas_frontend`)

```bash
cd saas_frontend
npm install
npm run dev
```

### 3. Database
You will need a running PostgreSQL instance. The easiest way is to use the docker-compose just for the DB:
```bash
docker-compose up -d db
```

---

## 🔑 Environment Variables
Create a `.env` file in `auth_server/`. key variables:

```ini
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your_jwt_secret
ENCRYPTION_KEY=your_fernet_key
```

## ❓ Need Help?
Contact the project lead or check `documentation/FILE_STRUCTURE.md` to locate the code you're looking for.
