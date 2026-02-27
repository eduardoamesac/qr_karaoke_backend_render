"""
Cache Manager - Sistema de caché en JSON para canciones y cuentas de mesas
Mantiene datos únicamente en JSON (no se usan más las tablas en BD)
Canciones se almacenan en un índice global centralizado
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
from timezone_utils import now_bogota

class CacheManager:
    """Gestor centralizado de caché para canciones, mesas, cuentas, consumos y song_credits"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Caché en memoria - Índice GLOBAL de canciones
        self.songs_index: Dict[int, Dict[str, Any]] = {}  # {cancion_id: cancion_data}
        self.next_song_id = 1  # Para generar IDs auto-incrementables
        
        # Caché por usuario (referencias a IDs globales)
        self.user_songs: Dict[int, List[int]] = {}  # {usuario_id: [cancion_ids]}
        
        # Caché en memoria de mesas
        self.mesas_data: Dict[int, Dict[str, Any]] = {}  # {mesa_id: mesa_data}
        self.next_mesa_id = 1
        
        # Caché en memoria de cuentas de mesas
        self.mesas_cache: Dict[int, Dict[str, Any]] = {}  # {mesa_id: {cuenta}}
        
        # Caché en memoria de consumos
        self.consumos_data: Dict[int, Dict[str, Any]] = {}  # {consumo_id: consumo_data}
        self.next_consumo_id = 1
        
        # Caché en memoria de song_credits
        self.song_credits_data: Dict[int, List[Dict[str, Any]]] = {}  # {usuario_id: [credits]}
        
        # Lock para evitar race conditions
        self.lock = threading.RLock()
        
        # Cargar caché existente
        self._load_cache()
    
    # ========================================================================
    # FUNCIONES DE CACHÉ GLOBAL DE CANCIONES
    # ========================================================================
    
    def _get_global_songs_file(self) -> Path:
        """Obtiene la ruta del archivo global de canciones"""
        return self.cache_dir / "canciones_global.json"
    
    def _get_user_songs_file(self, usuario_id: int) -> Path:
        """Obtiene la ruta del índice de canciones de un usuario"""
        return self.cache_dir / f"user_songs_{usuario_id}.json"
    
    def _load_global_songs(self) -> None:
        """Carga el índice global de canciones desde JSON"""
        cache_file = self._get_global_songs_file()
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.songs_index = data.get("canciones", {})
                    # Convertir claves a int
                    self.songs_index = {int(k): v for k, v in self.songs_index.items()}
                    self.next_song_id = data.get("next_id", max(self.songs_index.keys()) + 1 if self.songs_index else 1)
            except Exception as e:
                print(f"Error cargando caché global de canciones: {e}")
                self.songs_index = {}
                self.next_song_id = 1
        else:
            self.songs_index = {}
            self.next_song_id = 1
    
    def _save_global_songs(self) -> None:
        """Guarda el índice global de canciones a JSON"""
        cache_file = self._get_global_songs_file()
        try:
            # Convertir claves a string para JSON
            data = {
                "canciones": {str(k): v for k, v in self.songs_index.items()},
                "next_id": self.next_song_id
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error guardando caché global de canciones: {e}")
    
    def _load_user_songs(self, usuario_id: int) -> None:
        """Carga el índice de canciones de un usuario"""
        cache_file = self._get_user_songs_file(usuario_id)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_songs[usuario_id] = data.get("song_ids", [])
            except Exception as e:
                print(f"Error cargando canciones de usuario {usuario_id}: {e}")
                self.user_songs[usuario_id] = []
        else:
            self.user_songs[usuario_id] = []
    
    def _save_user_songs(self, usuario_id: int) -> None:
        """Guarda el índice de canciones de un usuario"""
        if usuario_id not in self.user_songs:
            return
        
        cache_file = self._get_user_songs_file(usuario_id)
        try:
            data = {"song_ids": self.user_songs[usuario_id]}
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error guardando canciones de usuario {usuario_id}: {e}")
    
    def add_song_to_cache(self, usuario_id: int, cancion: Dict[str, Any]) -> int:
        """Agrega una canción al caché global y la asocia a un usuario. Retorna el song_id."""
        with self.lock:
            # Generar ID si no existe
            if "id" not in cancion or cancion["id"] is None:
                cancion["id"] = self.next_song_id
                self.next_song_id += 1
            
            song_id = cancion["id"]
            
            # Asegurar timestamps
            if "created_at" not in cancion:
                cancion["created_at"] = now_bogota().isoformat()
            
            # Guardar en índice global
            self.songs_index[song_id] = cancion
            
            # Agregar a índice de usuario
            if usuario_id not in self.user_songs:
                self.user_songs[usuario_id] = []
            
            if song_id not in self.user_songs[usuario_id]:
                self.user_songs[usuario_id].append(song_id)
            
            # Persistir
            self._save_global_songs()
            self._save_user_songs(usuario_id)
            
            return song_id
    
    def get_song_by_id(self, cancion_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una canción por su ID en el índice global"""
        with self.lock:
            return self.songs_index.get(int(cancion_id))
    
    def get_songs_by_user(self, usuario_id: int) -> List[Dict[str, Any]]:
        """Obtiene todas las canciones de un usuario"""
        with self.lock:
            if usuario_id not in self.user_songs:
                self._load_user_songs(usuario_id)
            
            song_ids = self.user_songs[usuario_id]
            return [self.songs_index[sid] for sid in song_ids if sid in self.songs_index]
    
    def get_songs_by_estado(self, estado: str) -> List[Dict[str, Any]]:
        """Obtiene todas las canciones con un estado específico"""
        with self.lock:
            return [s for s in self.songs_index.values() if s.get("estado") == estado]
    
    def get_song_by_youtube_id(self, youtube_id: str, valid_states: List[str] = None) -> Optional[Dict[str, Any]]:
        """Obtiene una canción por su youtube_id (puede filtrar por estados)"""
        with self.lock:
            for song in self.songs_index.values():
                if song.get("youtube_id") == youtube_id:
                    if valid_states is None or song.get("estado") in valid_states:
                        return song
            return None
    
    def update_song_in_cache(self, cancion_id: int, updates: Dict[str, Any]) -> bool:
        """Actualiza una canción en el caché global"""
        with self.lock:
            if cancion_id in self.songs_index:
                self.songs_index[cancion_id].update(updates)
                self._save_global_songs()
                return True
            return False
    
    def delete_song_from_cache(self, cancion_id: int, usuario_id: int = None) -> bool:
        """Elimina una canción del caché global"""
        with self.lock:
            if cancion_id in self.songs_index:
                del self.songs_index[cancion_id]
                self._save_global_songs()
                
                # Remover de índices de usuario
                if usuario_id is not None and usuario_id in self.user_songs:
                    if cancion_id in self.user_songs[usuario_id]:
                        self.user_songs[usuario_id].remove(cancion_id)
                        self._save_user_songs(usuario_id)
                else:
                    # Buscar en todos los usuarios
                    for uid, song_ids in self.user_songs.items():
                        if cancion_id in song_ids:
                            song_ids.remove(cancion_id)
                            self._save_user_songs(uid)
                
                return True
            return False
    
    def get_all_songs(self) -> List[Dict[str, Any]]:
        """Obtiene todas las canciones"""
        with self.lock:
            return list(self.songs_index.values())
    
    def clear_all_songs(self) -> None:
        """Limpia todas las canciones del caché"""
        with self.lock:
            self.songs_index = {}
            self.user_songs = {}
            self.next_song_id = 1
            self._save_global_songs()
            # Limpiar archivos de usuarios
            for user_file in self.cache_dir.glob("user_songs_*.json"):
                user_file.unlink()
    
    # ========================================================================
    # FUNCIONES DE CACHÉ DE CUENTAS (MESAS)
    # ========================================================================
    
    def _get_mesa_cache_file(self, mesa_id: int) -> Path:
        """Obtiene la ruta del archivo de caché de cuenta de mesa"""
        return self.cache_dir / f"mesa_cuenta_{mesa_id}.json"
    
    def _load_mesa_cache(self, mesa_id: int) -> None:
        """Carga caché de cuenta de mesa desde JSON"""
        cache_file = self._get_mesa_cache_file(mesa_id)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.mesas_cache[mesa_id] = json.load(f)
            except Exception as e:
                print(f"Error cargando caché de mesa {mesa_id}: {e}")
                self.mesas_cache[mesa_id] = self._create_empty_mesa_cache(mesa_id)
        else:
            self.mesas_cache[mesa_id] = self._create_empty_mesa_cache(mesa_id)
    
    def _create_empty_mesa_cache(self, mesa_id: int) -> Dict[str, Any]:
        """Crea una estructura vacía de caché para mesa"""
        return {
            "mesa_id": mesa_id,
            "created_at": now_bogota().isoformat(),
            "consumos": [],
            "pagos": [],
            "total_consumido": 0.0,
            "total_pagado": 0.0,
            "saldo": 0.0
        }
    
    def _save_mesa_cache(self, mesa_id: int) -> None:
        """Guarda caché de cuenta de mesa a JSON"""
        if mesa_id not in self.mesas_cache:
            return
        
        cache_file = self._get_mesa_cache_file(mesa_id)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.mesas_cache[mesa_id], f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error guardando caché de mesa {mesa_id}: {e}")
    
    def add_consumo_to_mesa_cache(self, mesa_id: int, consumo: Dict[str, Any]) -> None:
        """Agrega un consumo al caché de la mesa"""
        with self.lock:
            if mesa_id not in self.mesas_cache:
                self._load_mesa_cache(mesa_id)
            
            self.mesas_cache[mesa_id]["consumos"].append(consumo)
            
            # Actualizar total consumido
            try:
                valor_total = float(consumo.get("valor_total", 0))
                self.mesas_cache[mesa_id]["total_consumido"] += valor_total
                self.mesas_cache[mesa_id]["saldo"] = (
                    self.mesas_cache[mesa_id]["total_consumido"] - 
                    self.mesas_cache[mesa_id]["total_pagado"]
                )
            except (ValueError, TypeError):
                pass
            
            self._save_mesa_cache(mesa_id)
    
    def add_pago_to_mesa_cache(self, mesa_id: int, pago: Dict[str, Any]) -> None:
        """Agrega un pago al caché de la mesa"""
        with self.lock:
            if mesa_id not in self.mesas_cache:
                self._load_mesa_cache(mesa_id)
            
            self.mesas_cache[mesa_id]["pagos"].append(pago)
            
            # Actualizar total pagado
            try:
                monto = float(pago.get("monto", 0))
                self.mesas_cache[mesa_id]["total_pagado"] += monto
                self.mesas_cache[mesa_id]["saldo"] = (
                    self.mesas_cache[mesa_id]["total_consumido"] - 
                    self.mesas_cache[mesa_id]["total_pagado"]
                )
            except (ValueError, TypeError):
                pass
            
            self._save_mesa_cache(mesa_id)
    
    def get_mesa_cuenta_from_cache(self, mesa_id: int) -> Dict[str, Any]:
        """Obtiene la información de cuenta de una mesa desde caché"""
        with self.lock:
            if mesa_id not in self.mesas_cache:
                self._load_mesa_cache(mesa_id)
            
            return self.mesas_cache[mesa_id].copy()
    
    def clear_mesa_cache(self, mesa_id: int) -> None:
        """Limpia el caché de una mesa"""
        with self.lock:
            if mesa_id in self.mesas_cache:
                del self.mesas_cache[mesa_id]
            
            cache_file = self._get_mesa_cache_file(mesa_id)
            if cache_file.exists():
                cache_file.unlink()
    
    # ========================================================================
    # FUNCIONES DE CACHÉ DE REVISIÓN DE COLA
    # ========================================================================
    
    def _get_queue_revision_cache_file(self) -> Path:
        """Obtiene la ruta del archivo de caché de revisión de cola"""
        return self.cache_dir / "queue_revision.json"
    
    def _load_queue_revision_cache(self) -> Dict[str, Any]:
        """Carga caché de revisión de cola desde JSON"""
        cache_file = self._get_queue_revision_cache_file()
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error cargando caché de revisión de cola: {e}")
        
        return {"revision": 0, "updated_at": now_bogota().isoformat()}
    
    def _save_queue_revision_cache(self, data: Dict[str, Any]) -> None:
        """Guarda caché de revisión de cola a JSON"""
        cache_file = self._get_queue_revision_cache_file()
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error guardando caché de revisión de cola: {e}")
    
    def get_queue_revision(self) -> int:
        """Obtiene la revisión actual de la cola desde caché"""
        with self.lock:
            data = self._load_queue_revision_cache()
            return int(data.get("revision", 0))
    
    def increment_queue_revision(self) -> int:
        """Incrementa la revisión de la cola y retorna el nuevo valor"""
        with self.lock:
            data = self._load_queue_revision_cache()
            new_revision = int(data.get("revision", 0)) + 1
            data["revision"] = new_revision
            data["updated_at"] = now_bogota().isoformat()
            self._save_queue_revision_cache(data)
            return new_revision
    
    def set_queue_revision(self, revision: int) -> None:
        """Establece la revisión de la cola a un valor específico"""
        with self.lock:
            data = self._load_queue_revision_cache()
            data["revision"] = revision
            data["updated_at"] = now_bogota().isoformat()
            self._save_queue_revision_cache(data)
    
    def _load_cache(self) -> None:
        """Carga todos los caché existentes al iniciar"""
        # Cargar caché global de canciones
        self._load_global_songs()
        
        # Cargar todos los caché de usuario
        for user_file in self.cache_dir.glob("user_songs_*.json"):
            try:
                usuario_id = int(user_file.stem.split('_')[-1])
                self._load_user_songs(usuario_id)
            except Exception as e:
                print(f"Error cargando {user_file}: {e}")
        
        # Cargar caché de mesas
        for mesa_file in self.cache_dir.glob("mesa_cuenta_*.json"):
            try:
                mesa_id = int(mesa_file.stem.split('_')[-1])
                self._load_mesa_cache(mesa_id)
            except Exception as e:
                print(f"Error cargando {mesa_file}: {e}")
        
        # Cargar caché de mesas completas
        self._load_mesas_data()
        
        # Cargar caché de consumos
        self._load_consumos_data()
        
        # Cargar caché de song_credits
        self._load_song_credits_data()
    
    # ========================================================================
    # FUNCIONES DE CACHÉ DE MESAS
    # ========================================================================
    
    def _get_mesas_file(self) -> Path:
        """Obtiene la ruta del archivo de mesas"""
        return self.cache_dir / "mesas.json"
    
    def _load_mesas_data(self) -> None:
        """Carga el índice de mesas desde JSON"""
        cache_file = self._get_mesas_file()
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.mesas_data = data.get("mesas", {})
                    self.mesas_data = {int(k): v for k, v in self.mesas_data.items()}
                    self.next_mesa_id = data.get("next_id", max(self.mesas_data.keys()) + 1 if self.mesas_data else 1)
            except Exception as e:
                print(f"Error cargando caché de mesas: {e}")
                self.mesas_data = {}
                self.next_mesa_id = 1
        else:
            self.mesas_data = {}
            self.next_mesa_id = 1
    
    def _save_mesas_data(self) -> None:
        """Guarda el índice de mesas a JSON"""
        cache_file = self._get_mesas_file()
        try:
            data = {
                "mesas": {str(k): v for k, v in self.mesas_data.items()},
                "next_id": self.next_mesa_id
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error guardando caché de mesas: {e}")
    
    def create_mesa_in_cache(self, nombre: str, qr_code: str) -> int:
        """Crea una mesa en caché y retorna el mesa_id"""
        with self.lock:
            import re
            
            # Intentar extraer el ID lógico de la mesa desde el qr_code o el nombre
            mesa_id = None
            match_qr = re.search(r'karaoke-mesa-(\d+)', qr_code, re.IGNORECASE)
            if match_qr:
                mesa_id = int(match_qr.group(1))
            else:
                match_name = re.search(r'Mesa\s+(\d+)', nombre, re.IGNORECASE)
                if match_name:
                    mesa_id = int(match_name.group(1))
            
            # Si no pudimos extraer el ID o si ese ID ya está en uso de forma excepcional
            if mesa_id is None or mesa_id in self.mesas_data:
                # Asegurar de no chocar con ningún ID existente al usar el next_mesa_id
                while self.next_mesa_id in self.mesas_data:
                    self.next_mesa_id += 1
                mesa_id = self.next_mesa_id
                self.next_mesa_id += 1
            
            # Actualizar el next_mesa_id global si nuestro ID actual es más alto
            if mesa_id >= self.next_mesa_id:
                self.next_mesa_id = mesa_id + 1
            
            self.mesas_data[mesa_id] = {
                "id": mesa_id,
                "nombre": nombre,
                "qr_code": qr_code,
                "is_active": True,
                "created_at": now_bogota().isoformat()
            }
            
            self._save_mesas_data()
            return mesa_id
    
    def get_mesa_by_id(self, mesa_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una mesa por su ID"""
        with self.lock:
            return self.mesas_data.get(mesa_id)
    
    def get_mesa_by_qr(self, qr_code: str) -> Optional[Dict[str, Any]]:
        """Obtiene una mesa por su código QR"""
        with self.lock:
            for mesa in self.mesas_data.values():
                if mesa.get("qr_code") == qr_code:
                    return mesa
            return None
    
    def get_all_mesas(self) -> List[Dict[str, Any]]:
        """Obtiene todas las mesas"""
        with self.lock:
            return list(self.mesas_data.values())
    
    def update_mesa_in_cache(self, mesa_id: int, updates: Dict[str, Any]) -> bool:
        """Actualiza los datos de una mesa"""
        with self.lock:
            if mesa_id in self.mesas_data:
                self.mesas_data[mesa_id].update(updates)
                self._save_mesas_data()
                return True
            return False
    
    def delete_mesa_from_cache(self, mesa_id: int) -> bool:
        """Elimina una mesa del caché"""
        with self.lock:
            if mesa_id in self.mesas_data:
                del self.mesas_data[mesa_id]
                self._save_mesas_data()
                self.clear_mesa_cache(mesa_id)
                return True
            return False
    
    # ========================================================================
    # FUNCIONES DE CACHÉ DE CONSUMOS
    # ========================================================================
    
    def _get_consumos_file(self) -> Path:
        """Obtiene la ruta del archivo de consumos"""
        return self.cache_dir / "consumos.json"
    
    def _load_consumos_data(self) -> None:
        """Carga el índice de consumos desde JSON"""
        cache_file = self._get_consumos_file()
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.consumos_data = data.get("consumos", {})
                    self.consumos_data = {int(k): v for k, v in self.consumos_data.items()}
                    self.next_consumo_id = data.get("next_id", max(self.consumos_data.keys()) + 1 if self.consumos_data else 1)
            except Exception as e:
                print(f"Error cargando caché de consumos: {e}")
                self.consumos_data = {}
                self.next_consumo_id = 1
        else:
            self.consumos_data = {}
            self.next_consumo_id = 1
    
    def _save_consumos_data(self) -> None:
        """Guarda el índice de consumos a JSON"""
        cache_file = self._get_consumos_file()
        try:
            data = {
                "consumos": {str(k): v for k, v in self.consumos_data.items()},
                "next_id": self.next_consumo_id
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error guardando caché de consumos: {e}")
    
    def create_consumo_in_cache(self, consumo_data: Dict[str, Any]) -> int:
        """Crea un consumo en caché y retorna el consumo_id"""
        with self.lock:
            consumo_id = self.next_consumo_id
            self.next_consumo_id += 1
            
            consumo_data["id"] = consumo_id
            if "created_at" not in consumo_data:
                consumo_data["created_at"] = now_bogota().isoformat()
            
            self.consumos_data[consumo_id] = consumo_data
            
            # Agregar a caché de mesa también
            if "mesa_id" in consumo_data:
                self.add_consumo_to_mesa_cache(consumo_data["mesa_id"], consumo_data)
            
            self._save_consumos_data()
            return consumo_id
    
    def get_consumo_by_id(self, consumo_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un consumo por su ID"""
        with self.lock:
            return self.consumos_data.get(consumo_id)
    
    def get_consumos_by_mesa(self, mesa_id: int) -> List[Dict[str, Any]]:
        """Obtiene todos los consumos de una mesa"""
        with self.lock:
            return [c for c in self.consumos_data.values() if c.get("mesa_id") == mesa_id]
    
    def get_consumos_by_usuario(self, usuario_id: int) -> List[Dict[str, Any]]:
        """Obtiene todos los consumos de un usuario"""
        with self.lock:
            return [c for c in self.consumos_data.values() if c.get("usuario_id") == usuario_id]
    
    def get_all_consumos(self) -> List[Dict[str, Any]]:
        """Obtiene todos los consumos"""
        with self.lock:
            return list(self.consumos_data.values())
    
    def update_consumo_in_cache(self, consumo_id: int, updates: Dict[str, Any]) -> bool:
        """Actualiza un consumo en caché"""
        with self.lock:
            if consumo_id in self.consumos_data:
                self.consumos_data[consumo_id].update(updates)
                self._save_consumos_data()
                return True
            return False
    
    def delete_consumo_from_cache(self, consumo_id: int) -> bool:
        """Elimina un consumo del caché"""
        with self.lock:
            if consumo_id in self.consumos_data:
                del self.consumos_data[consumo_id]
                self._save_consumos_data()
                return True
            return False
    
    # ========================================================================
    # FUNCIONES DE CACHÉ DE SONG CREDITS
    # ========================================================================
    
    def _get_song_credits_file(self, usuario_id: int) -> Path:
        """Obtiene la ruta del archivo de song_credits de un usuario"""
        return self.cache_dir / f"song_credits_{usuario_id}.json"
    
    def _load_song_credits_data(self) -> None:
        """Carga los song_credits desde JSON"""
        for credits_file in self.cache_dir.glob("song_credits_*.json"):
            try:
                usuario_id = int(credits_file.stem.split('_')[-1])
                with open(credits_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.song_credits_data[usuario_id] = data.get("credits", [])
            except Exception as e:
                print(f"Error cargando song_credits de usuario {usuario_id}: {e}")
                self.song_credits_data[usuario_id] = []
    
    def _save_song_credits_data(self, usuario_id: int) -> None:
        """Guarda los song_credits de un usuario a JSON"""
        if usuario_id not in self.song_credits_data:
            return
        
        cache_file = self._get_song_credits_file(usuario_id)
        try:
            data = {"credits": self.song_credits_data[usuario_id]}
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error guardando song_credits de usuario {usuario_id}: {e}")
    
    def add_song_credits(self, usuario_id: int, credits_value: int, metodo: str = "producto") -> None:
        """Agrega créditos de canción a un usuario"""
        with self.lock:
            if usuario_id not in self.song_credits_data:
                self.song_credits_data[usuario_id] = []
            
            credit_record = {
                "id": len(self.song_credits_data[usuario_id]) + 1,
                "credits_value": credits_value,
                "created_at": now_bogota().isoformat(),
                "expires_at": None,
                "consumed_at": None,
                "metodo": metodo
            }
            
            self.song_credits_data[usuario_id].append(credit_record)
            self._save_song_credits_data(usuario_id)
    
    def get_song_credits(self, usuario_id: int) -> List[Dict[str, Any]]:
        """Obtiene todos los song_credits de un usuario"""
        with self.lock:
            if usuario_id not in self.song_credits_data:
                return []
            return self.song_credits_data[usuario_id]
    
    def get_active_song_credits(self, usuario_id: int) -> int:
        """Obtiene los créditos activos (no consumidos) de un usuario"""
        with self.lock:
            if usuario_id not in self.song_credits_data:
                return 0
            
            total = 0
            for credit in self.song_credits_data[usuario_id]:
                if credit.get("consumed_at") is None and credit.get("expires_at") is None:
                    total += credit.get("credits_value", 0)
            return total
    
    def consume_song_credits(self, usuario_id: int, song_id: int) -> bool:
        """Marca un crédito como consumido"""
        with self.lock:
            if usuario_id not in self.song_credits_data:
                return False
            
            # Encontrar el primer crédito no consumido
            for credit in self.song_credits_data[usuario_id]:
                if credit.get("consumed_at") is None:
                    credit["consumed_at"] = now_bogota().isoformat()
                    credit["consumed_by_song_id"] = song_id
                    self._save_song_credits_data(usuario_id)
                    return True
            
            return False
    
    def clear_song_credits(self, usuario_id: int) -> None:
        """Limpia todos los song_credits de un usuario"""
        with self.lock:
            if usuario_id in self.song_credits_data:
                del self.song_credits_data[usuario_id]
            
            cache_file = self._get_song_credits_file(usuario_id)
            if cache_file.exists():
                cache_file.unlink()
    
    # ========================================================================
    # ALIAS PARA COMPATIBILIDAD
    # ========================================================================
    
    def create_mesa(self, mesa_data: dict) -> int:
        """Alias para create_mesa_in_cache"""
        return self.create_mesa_in_cache(mesa_data.get("nombre"), mesa_data.get("qr_code"))
    
    def update_mesa(self, mesa_id: int, updates: dict) -> bool:
        """Alias para update_mesa_in_cache"""
        return self.update_mesa_in_cache(mesa_id, updates)
    
    def add_song(self, cancion_data: dict) -> int:
        """Alias para add_song_to_cache"""
        usuario_id = cancion_data.get("usuario_id", 0)
        return self.add_song_to_cache(usuario_id, cancion_data)
    
    def update_song(self, cancion_id: int, updates: dict) -> bool:
        """Alias para update_song_in_cache"""
        return self.update_song_in_cache(cancion_id, updates)
    
    def add_consumo(self, consumo_data: dict) -> int:
        """Alias para add_consumo_to_mesa_cache - retorna consumo_id"""
        mesa_id = consumo_data.get("mesa_id")
        if mesa_id:
            self.add_consumo_to_mesa_cache(mesa_id, consumo_data)
            # Generar ID para el consumo
            if not hasattr(self, '_consumo_id_counter'):
                self._consumo_id_counter = 1
            consumo_id = self._consumo_id_counter
            self._consumo_id_counter += 1
            consumo_data["id"] = consumo_id
            return consumo_id
        return None
    
    def clear_all(self) -> None:
        """Limpia todos los caché"""
        self.clear_all_songs()
        # Limpiar mesas
        for mesa_id in list(self.mesas_data.keys()):
            self.clear_mesa_cache(mesa_id)

# Instancia global del cache manager
cache_manager = CacheManager()
