import sys
import os
from sqlalchemy.orm import Session

# Add local path to import modules
sys.path.append(os.getcwd())

from database import SessionLocal
import models
import crud
import schemas
from cache_manager import cache_manager as cache

def verify_reset():
    db = SessionLocal()
    try:
        # 1. Setup - Create test data in cache and DB
        print("--- Setting up test data ---")
        user = db.query(models.Usuario).first()
        if not user:
            print("❌ No user found")
            return
            
        # Give credits and assign mesa
        user.song_credits = 500
        user.puntos = 1000
        user.mesa_id = 1
        user.is_active = True
        db.add(user)
        db.commit()
        
        # Add a song to cache
        cache.add_song_to_cache(user.id, {"titulo": "Test Song", "youtube_id": "123", "estado": "pendiente"})
        # Add a consumption to cache
        cache.add_consumo_to_mesa_cache(1, {"producto_id": 1, "cantidad": 1, "valor_total": 10.0})
        
        print("Data setup complete.")

        # 2. Call Reset Night
        print("--- Calling Reset Night ---")
        crud.reset_database_for_new_night(db)
        
        # 3. Verification
        print("--- Verifying ---")
        
        # Check cache
        songs = cache.get_all_songs()
        consumos = cache.get_all_consumos()
        if len(songs) == 0 and len(consumos) == 0:
            print("✅ Cache cleared correctly (Songs: 0, Consumos: 0)")
        else:
            print(f"❌ Cache NOT cleared: Songs={len(songs)}, Consumos={len(consumos)}")
            
        # Check DB
        db.refresh(user)
        if user.song_credits == 0 and user.puntos == 0 and user.mesa_id is None and user.is_active == False:
            print("✅ Database user fields reset correctly")
        else:
            print(f"❌ DB NOT reset: Credits={user.song_credits}, Puntos={user.puntos}, Mesa={user.mesa_id}, Active={user.is_active}")

    finally:
        db.close()

if __name__ == "__main__":
    verify_reset()
