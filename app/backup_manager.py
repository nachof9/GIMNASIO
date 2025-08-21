import sqlite3
import shutil
import gzip
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import threading
import time
from .config import get_backup_path, get_data_path, BACKUP_CONFIG, generate_backup_filename

class BackupManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backup_path = get_backup_path()
        self.backup_path.mkdir(exist_ok=True)
        self.auto_backup_thread = None
        self.stop_auto_backup = False
        
    def create_backup(self, description: str = "") -> Dict[str, any]:
        """Crea un backup incremental de la base de datos"""
        try:
            backup_filename = generate_backup_filename()
            backup_file_path = self.backup_path / backup_filename
            
            # Crear backup de la base de datos
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(str(backup_file_path))
            
            source_conn.backup(backup_conn)
            source_conn.close()
            backup_conn.close()
            
            # Calcular hash para verificación de integridad
            file_hash = self._calculate_file_hash(backup_file_path)
            
            # Crear metadata del backup
            metadata = {
                "filename": backup_filename,
                "created_at": datetime.now().isoformat(),
                "description": description,
                "file_size": backup_file_path.stat().st_size,
                "hash": file_hash,
                "compressed": False
            }
            
            # Guardar metadata
            self._save_backup_metadata(backup_filename, metadata)
            
            # Limpiar backups antiguos
            self._cleanup_old_backups()
            
            return {
                "success": True,
                "filename": backup_filename,
                "path": str(backup_file_path),
                "metadata": metadata
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def restore_backup(self, backup_filename: str) -> Dict[str, any]:
        """Restaura la base de datos desde un backup"""
        try:
            backup_file_path = self.backup_path / backup_filename
            
            if not backup_file_path.exists():
                # Verificar si existe comprimido
                compressed_path = self.backup_path / f"{backup_filename}.gz"
                if compressed_path.exists():
                    backup_file_path = compressed_path
                else:
                    return {"success": False, "error": "Archivo de backup no encontrado"}
            
            # Verificar integridad del backup
            if not self._verify_backup_integrity(backup_filename):
                return {"success": False, "error": "El backup está corrupto"}
            
            # Crear backup de seguridad de la DB actual
            current_backup = self.create_backup("Backup antes de restauración")
            
            # Descomprimir si es necesario
            restore_file = backup_file_path
            if backup_filename.endswith('.gz') or str(backup_file_path).endswith('.gz'):
                restore_file = self._decompress_backup(backup_file_path)
            
            # Restaurar base de datos
            shutil.copy2(restore_file, self.db_path)
            
            # Limpiar archivo temporal si se descomprimió
            if restore_file != backup_file_path:
                restore_file.unlink()
            
            return {
                "success": True,
                "message": "Base de datos restaurada exitosamente",
                "safety_backup": current_backup.get("filename") if current_backup.get("success") else None
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_backup_list(self) -> List[Dict]:
        """Obtiene lista de backups disponibles"""
        backups = []
        metadata_file = self.backup_path / "backup_metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
                
                for filename, metadata in all_metadata.items():
                    backup_file = self.backup_path / filename
                    compressed_file = self.backup_path / f"{filename}.gz"
                    if backup_file.exists() or compressed_file.exists():
                        backups.append(metadata)
                
                # Ordenar por fecha de creación (más reciente primero)
                backups.sort(key=lambda x: x['created_at'], reverse=True)
                
            except Exception as e:
                print(f"Error al leer metadata de backups: {e}")
        
        return backups
    
    def start_auto_backup(self):
        """Inicia el sistema de backup automático"""
        if self.auto_backup_thread and self.auto_backup_thread.is_alive():
            return
        
        self.stop_auto_backup = False
        self.auto_backup_thread = threading.Thread(target=self._auto_backup_worker, daemon=True)
        self.auto_backup_thread.start()
    
    def stop_auto_backup_system(self):
        """Detiene el sistema de backup automático"""
        self.stop_auto_backup = True
        if self.auto_backup_thread:
            self.auto_backup_thread.join(timeout=5)
    
    def _auto_backup_worker(self):
        """Worker thread para backups automáticos"""
        backup_interval = BACKUP_CONFIG["auto_backup_hours"] * 3600  # Convertir a segundos
        
        while not self.stop_auto_backup:
            try:
                # Esperar el intervalo de backup
                for _ in range(backup_interval):
                    if self.stop_auto_backup:
                        return
                    time.sleep(1)
                
                # Crear backup automático
                result = self.create_backup("Backup automático")
                if result["success"]:
                    print(f"Backup automático creado: {result['filename']}")
                else:
                    print(f"Error en backup automático: {result['error']}")
                    
            except Exception as e:
                print(f"Error en worker de backup automático: {e}")
                time.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcula hash SHA256 de un archivo"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _verify_backup_integrity(self, backup_filename: str) -> bool:
        """Verifica la integridad de un backup"""
        if not BACKUP_CONFIG["verify_integrity"]:
            return True
        
        try:
            metadata = self._get_backup_metadata(backup_filename)
            if not metadata:
                return False
            
            backup_file_path = self.backup_path / backup_filename
            compressed_file_path = self.backup_path / f"{backup_filename}.gz"
            
            # Determinar qué archivo verificar
            if compressed_file_path.exists():
                current_hash = self._calculate_file_hash(compressed_file_path)
            elif backup_file_path.exists():
                current_hash = self._calculate_file_hash(backup_file_path)
            else:
                return False
            
            return current_hash == metadata.get("hash")
            
        except Exception as e:
            print(f"Error verificando integridad de backup: {e}")
            return False
    
    def _save_backup_metadata(self, filename: str, metadata: Dict):
        """Guarda metadata de un backup"""
        metadata_file = self.backup_path / "backup_metadata.json"
        
        all_metadata = {}
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
            except:
                pass
        
        all_metadata[filename] = metadata
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(all_metadata, f, indent=2, ensure_ascii=False)
    
    def _get_backup_metadata(self, filename: str) -> Optional[Dict]:
        """Obtiene metadata de un backup específico"""
        metadata_file = self.backup_path / "backup_metadata.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                all_metadata = json.load(f)
            return all_metadata.get(filename)
        except:
            return None
    
    def _cleanup_old_backups(self):
        """Limpia backups antiguos y comprime los que corresponda"""
        try:
            backups = self.get_backup_list()
            max_backups = BACKUP_CONFIG["max_backups"]
            compress_after_days = BACKUP_CONFIG["compress_after_days"]
            
            # Comprimir backups antiguos
            cutoff_date = datetime.now() - timedelta(days=compress_after_days)
            
            for backup in backups:
                backup_date = datetime.fromisoformat(backup["created_at"])
                filename = backup["filename"]
                
                if backup_date < cutoff_date and not backup.get("compressed", False):
                    self._compress_backup_file(filename)
            
            # Eliminar backups excedentes
            if len(backups) > max_backups:
                backups_to_delete = backups[max_backups:]
                for backup in backups_to_delete:
                    self._delete_backup(backup["filename"])
                    
        except Exception as e:
            print(f"Error en limpieza de backups: {e}")
    
    def _compress_backup_file(self, filename: str):
        """Comprime un archivo de backup"""
        try:
            backup_file = self.backup_path / filename
            compressed_file = self.backup_path / f"{filename}.gz"
            
            if not backup_file.exists() or compressed_file.exists():
                return
            
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Actualizar metadata
            metadata = self._get_backup_metadata(filename)
            if metadata:
                metadata["compressed"] = True
                metadata["compressed_size"] = compressed_file.stat().st_size
                self._save_backup_metadata(filename, metadata)
            
            # Eliminar archivo original
            backup_file.unlink()
            
        except Exception as e:
            print(f"Error comprimiendo backup {filename}: {e}")
    
    def _decompress_backup(self, compressed_file: Path) -> Path:
        """Descomprime un backup para restauración"""
        temp_file = compressed_file.with_suffix('')
        
        with gzip.open(compressed_file, 'rb') as f_in:
            with open(temp_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return temp_file
    
    def _delete_backup(self, filename: str):
        """Elimina un backup y su metadata"""
        try:
            # Eliminar archivo de backup
            backup_file = self.backup_path / filename
            compressed_file = self.backup_path / f"{filename}.gz"
            
            if backup_file.exists():
                backup_file.unlink()
            if compressed_file.exists():
                compressed_file.unlink()
            
            # Eliminar metadata
            metadata_file = self.backup_path / "backup_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
                
                if filename in all_metadata:
                    del all_metadata[filename]
                    
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(all_metadata, f, indent=2, ensure_ascii=False)
                        
        except Exception as e:
            print(f"Error eliminando backup {filename}: {e}")
