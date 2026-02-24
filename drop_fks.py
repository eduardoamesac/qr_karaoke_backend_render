import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def drop_fk_constraints():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "mi_base_datos")
        )
        cursor = conn.cursor()
        
        # 1. Buscar nombres de constraints para usuarios.mesa_id
        cursor.execute("""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_NAME = 'usuarios' AND COLUMN_NAME = 'mesa_id' AND TABLE_SCHEMA = %s
        """, (os.getenv("DB_NAME", "mi_base_datos"),))
        
        constraints = cursor.fetchall()
        for (constraint_name,) in constraints:
            if constraint_name != 'PRIMARY':
                print(f"Dropping constraint {constraint_name} from usuarios...")
                try:
                    cursor.execute(f"ALTER TABLE usuarios DROP FOREIGN KEY {constraint_name}")
                except Exception as e:
                    print(f"Error dropping {constraint_name}: {e}")

        # 2. Buscar nombres de constraints para pagos.mesa_id
        cursor.execute("""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_NAME = 'pagos' AND COLUMN_NAME = 'mesa_id' AND TABLE_SCHEMA = %s
        """, (os.getenv("DB_NAME", "mi_base_datos"),))
        
        constraints = cursor.fetchall()
        for (constraint_name,) in constraints:
            if constraint_name != 'PRIMARY':
                print(f"Dropping constraint {constraint_name} from pagos...")
                try:
                    cursor.execute(f"ALTER TABLE pagos DROP FOREIGN KEY {constraint_name}")
                except Exception as e:
                    print(f"Error dropping {constraint_name}: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Done.")
    except Exception as e:
        print(f"Failed to connect or execute: {e}")

if __name__ == "__main__":
    drop_fk_constraints()
