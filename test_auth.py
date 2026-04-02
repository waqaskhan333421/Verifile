from services.auth import hash_password, verify_password

h = hash_password("test123")
print(f"Hash: {h}")
print(f"Verify: {verify_password('test123', h)}")
