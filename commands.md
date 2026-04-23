# Commands Used

```powershell
# Create/activate venv
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install MySQL connector (if missing)
pip install mysql-connector-python

# Install JWT dependency (if missing)
pip install "python-jose[cryptography]"

# Run Alembic migrations (heads)
alembic upgrade heads

# Start the server
uvicorn main:app --reload
```

## Optional (MySQL setup)

```sql
CREATE DATABASE IF NOT EXISTS karaoke_db;

CREATE USER 'karaoke'@'localhost' IDENTIFIED BY 'zxc12345';
GRANT ALL PRIVILEGES ON karaoke_db.* TO 'karaoke'@'localhost';
FLUSH PRIVILEGES;
```

