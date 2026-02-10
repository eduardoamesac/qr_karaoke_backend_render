import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from database import SessionLocal
    from queue_manager import queue_manager
    from models import Cancion
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def verify_queue():
    print("--- Verifying QueueManager Singleton ---")
    db = SessionLocal()
    try:
        # 1. Check initial state (might be empty if not refreshed)
        print("Initial queue state:", len(queue_manager._approved_queue))
        
        # 2. Refresh
        print("Refreshing queue from DB...")
        q = queue_manager.refresh_queue(db)
        print(f"Queue size after refresh: {len(q)}")
        
        if q:
            print(f"First song: {q[0].titulo} (ID: {q[0].id})")
            print(f"Order Manual: {q[0].orden_manual}")
            # Verify attachment by accessing relationship
            if q[0].usuario:
                print(f"User Nick: {q[0].usuario.nick}")
            print(f"Mesa ID: {q[0].usuario.mesa_id if q[0].usuario else 'None'}")
        else:
            print("Queue is empty.")
            
        # 3. Validation
        # Check if queue_manager instance is same if imported again
        from queue_manager import queue_manager as qm2
        if queue_manager is qm2:
            print("Singleton check: PASS")
        else:
            print("Singleton check: FAIL")
            
        # 4. Test pop_next_song state change
        print("\nTesting pop_next_song state change...")
        popped_song = queue_manager.pop_next_song(db)
        if popped_song:
            print(f"Popped song: {popped_song.titulo} (ID: {popped_song.id})")
            # Clear session to force re-fetch from DB
            db.expire_all()
            db_song = db.query(Cancion).filter(Cancion.id == popped_song.id).first()
            print(f"DB Status: {db_song.estado}")
            print(f"DB Started At: {db_song.started_at}")
            if db_song.estado == "reproduciendo" and db_song.started_at is not None:
                print("State Sync Test: PASS")
            else:
                print("State Sync Test: FAIL")
        else:
            print("No song to pop.")

    except Exception as e:
        print(f"Error during verification: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_queue()
