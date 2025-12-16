"""
重置管理員密碼
"""
import bcrypt

password = "louis1220"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print(f"Password: {password}")
print(f"Bcrypt Hash: {hashed}")
print("\nSQL 更新語句:")
print(f"UPDATE users SET hashed_password = '{hashed}' WHERE email = 'thankcoom@gmail.com';")
