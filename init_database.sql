-- Louis AS Grid - PostgreSQL 資料庫初始化腳本
-- 連接方式: psql "postgresql://root:0E8kuLQyzJOVe4ia9H1s7Y2nC6o5MTS3@sjc1.clusters.zeabur.com:24079/zeabur"

-- 創建 users 表
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    username VARCHAR UNIQUE,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    status VARCHAR DEFAULT 'pending_api',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    exchange VARCHAR DEFAULT 'bitget',
    exchange_uid VARCHAR UNIQUE,
    api_verified_at TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by VARCHAR,
    group_id VARCHAR,
    verified_invite_code VARCHAR,
    zeabur_url VARCHAR
);

-- 創建 invite_codes 表
CREATE TABLE IF NOT EXISTS invite_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR UNIQUE NOT NULL,
    exchange VARCHAR DEFAULT 'bitget',
    exchange_uid VARCHAR,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    used_by_user_id VARCHAR REFERENCES users(id)
);

-- 創建 groups 表
CREATE TABLE IF NOT EXISTS groups (
    id VARCHAR PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 創建 credentials 表
CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    exchange VARCHAR DEFAULT 'bitget',
    api_key_encrypted BYTEA NOT NULL,
    api_secret_encrypted BYTEA NOT NULL,
    passphrase_encrypted BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入管理員帳號（密碼：louis1220，bcrypt 加密）
INSERT INTO users (
    id, 
    email, 
    username, 
    hashed_password, 
    is_active, 
    is_admin, 
    status, 
    exchange,
    created_at
) VALUES (
    'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d',
    'thankcoom@gmail.com',
    'thankcoom',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5/6UzFE0YEwC6',
    TRUE,
    TRUE,
    'active',
    'bitget',
    CURRENT_TIMESTAMP
)
ON CONFLICT (email) DO UPDATE 
SET is_admin = TRUE, status = 'active';

-- 驗證
SELECT id, email, username, is_admin, status, created_at 
FROM users 
WHERE email = 'thankcoom@gmail.com';
