from sqlalchemy import create_engine
from database import Base
# Import all models so Base.metadata knows about them
from models import Mesa, Usuario, Cancion, Producto, Consumo, BannedNick, AdminLog, AdminApiKey, Pago, Cuenta, ConfiguracionGlobal
import settings_storage # In case there are more models or side effects

# MySQL connection string
# Using pymysql driver with port 3307
MYSQL_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3307/mi_base_datos"

def create_schema():
    print("Connecting to MySQL...")
    engine = create_engine(MYSQL_DATABASE_URL)
    
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully in MySQL!")

if __name__ == "__main__":
    create_schema()
