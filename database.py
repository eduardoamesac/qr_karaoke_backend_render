from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Conexión a MySQL
# Usuario: root, Contraseña: 1234, Puerto: 3307, Base de datos: mi_base_datos
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3307/mi_base_datos"

# MySQL no necesita connect_args especiales como SQLite
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()