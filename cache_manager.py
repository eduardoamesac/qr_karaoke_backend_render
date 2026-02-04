"""
Cache Manager - Sistema de caché en JSON para canciones y cuentas de mesas
Mantiene datos en memoria (JSON) para mejor performance
Sincroniza con BD solo cuando es necesario
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
from timezone_utils import now_bogota

class CacheManager:
    """Gestor centralizado de caché para canciones y cuentas"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Caché en memoria
        self.songs_cache: Dict[int, Dict[str, Any]] = {}  # {usuario_id: {canciones}}
        self.mesas_cache: Dict[int, Dict[str, Any]] = {}  # {mesa_id: {cuenta}}
        
        # Lock para evitar race conditions
        self.lock = threading.RLock()
        
        # Cargar caché existente
        self._load_cache()
    
    # ========================================================================
    # FUNCIONES DE CACHÉ DE CANCIONES
    # ========================================================================
    
    def _get_songs_cache_file(self, usuario_id: int) -> Path:
        """Obtiene la ruta del archivo de caché de canciones"""
        return self.cache_dir / f"songs_usuario_{usuario_id}.json"
    
    def _load_songs_cache(self, usuario_id: int) -> None:
        """Carga caché de canciones desde JSON"""
        cache_file = self._get_songs_cache_file(usuario_id)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.songs_cache[usuario_id] = json.load(f)
            except Exception as e:
                print(f"Error cargando caché de canciones {usuario_id}: {e}")
                self.songs_cache[usuario_id] = {"canciones": []}
        else:
            self.songs_cache[usuario_id] = {"canciones": []}
    
    def _save_songs_cache(self, usuario_id: int) -> None:
        """Guarda caché de canciones a JSON"""
        if usuario_id not in self.songs_cache:
            return
        
        cache_file = self._get_songs_cache_file(usuario_id)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.songs_cache[usuario_id], f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error guardando caché de canciones {usuario_id}: {e}")
    
    def add_song_to_cache(self, usuario_id: int, cancion: Dict[str, Any]) -> None:
        """Agrega una canción al caché"""
        with self.lock:
            if usuario_id not in self.songs_cache:
                self._load_songs_cache(usuario_id)
            
            # Asegurar que 'canciones' existe
            if "canciones" not in self.songs_cache[usuario_id]:
                self.songs_cache[usuario_id]["canciones"] = []
            
            self.songs_cache[usuario_id]["canciones"].append(cancion)
            self._save_songs_cache(usuario_id)
    
    def get_songs_from_cache(self, usuario_id: int) -> List[Dict[str, Any]]:
        """Obtiene todas las canciones del caché de un usuario"""
        with self.lock:
            if usuario_id not in self.songs_cache:
                self._load_songs_cache(usuario_id)
            
            return self.songs_cache[usuario_id].get("canciones", [])
    
    def update_song_in_cache(self, usuario_id: int, cancion_id: int, updates: Dict[str, Any]) -> bool:
        """Actualiza una canción en el caché"""
        with self.lock:
            if usuario_id not in self.songs_cache:
                self._load_songs_cache(usuario_id)
            
            canciones = self.songs_cache[usuario_id].get("canciones", [])
            for cancion in canciones:
                if cancion.get("id") == cancion_id:
                    cancion.update(updates)
                    self._save_songs_cache(usuario_id)
                    return True
            
            return False
    
    def delete_song_from_cache(self, usuario_id: int, cancion_id: int) -> bool:
        """Elimina una canción del caché"""
        with self.lock:
            if usuario_id not in self.songs_cache:
                self._load_songs_cache(usuario_id)
            
            canciones = self.songs_cache[usuario_id].get("canciones", [])
            original_len = len(canciones)
            
            self.songs_cache[usuario_id]["canciones"] = [
                c for c in canciones if c.get("id") != cancion_id
            ]
            
            if len(self.songs_cache[usuario_id]["canciones"]) < original_len:
                self._save_songs_cache(usuario_id)
                return True
            
            return False
    
    def clear_songs_cache(self, usuario_id: int) -> None:
        """Limpia el caché de canciones de un usuario"""
        with self.lock:
            self.songs_cache[usuario_id] = {"canciones": []}
            cache_file = self._get_songs_cache_file(usuario_id)
            if cache_file.exists():
                cache_file.unlink()
    
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
    
    def _load_cache(self) -> None:
        """Carga todos los caché existentes al iniciar"""
        # Cargar todos los archivos de caché
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if "usuario_id" in cache_file.name:
                        # Es caché de canciones
                        usuario_id = int(cache_file.stem.split('_')[-1])
                        self.songs_cache[usuario_id] = data
                    elif "mesa_cuenta" in cache_file.name:
                        # Es caché de mesa
                        mesa_id = int(cache_file.stem.split('_')[-1])
                        self.mesas_cache[mesa_id] = data
            except Exception as e:
                print(f"Error cargando {cache_file}: {e}")

# Instancia global del cache manager
cache_manager = CacheManager()
