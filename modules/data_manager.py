# data_manager.py
import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

class DataManager:
    def __init__(self):
        self.data_dir = "data"
        self.backup_dir = os.path.join(self.data_dir, "backups")
        self._ensure_directories()
        self.logger = logging.getLogger('DataManager')

    def _ensure_directories(self):
        """确保所有数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

    def safe_save(self, filename: str, data: Any, backup: bool = True) -> bool:
        """安全保存数据文件"""
        path = os.path.join(self.data_dir, filename)
        try:
            # 先保存到临时文件
            temp_path = f"{path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 替换原文件
            if os.path.exists(path):
                if backup:
                    self._create_backup(path)
                os.remove(path)
            os.rename(temp_path, path)
            return True
        except Exception as e:
            self.logger.error(f"保存文件{filename}失败: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    def safe_load(self, filename: str, default: Any = None) -> Any:
        """安全加载数据文件"""
        path = os.path.join(self.data_dir, filename)
        try:
            if not os.path.exists(path):
                return default
                
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 验证基本数据完整性
                if not isinstance(data, (dict, list)):
                    raise ValueError("Invalid data format")
                return data
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"数据文件{filename}损坏，尝试恢复备份")
            return self._restore_backup(filename, default)
        except Exception as e:
            self.logger.error(f"加载文件{filename}失败: {str(e)}")
            return default

    def _create_backup(self, original_path: str):
        """创建备份文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(original_path)}.{timestamp}.bak"
        backup_path = os.path.join(self.backup_dir, backup_name)
        try:
            with open(original_path, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
        except Exception as e:
            self.logger.error(f"创建备份失败: {str(e)}")

    def _restore_backup(self, filename: str, default: Any) -> Any:
        """尝试恢复备份"""
        try:
            backups = sorted(
                [f for f in os.listdir(self.backup_dir) if f.startswith(filename)],
                reverse=True
            )
            if backups:
                latest_backup = os.path.join(self.backup_dir, backups[0])
                with open(latest_backup, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"恢复备份失败: {str(e)}")
        
        self.logger.info(f"使用默认数据恢复{filename}")
        return default

    def validate_data_structure(self, data: Any, schema: Dict) -> bool:
        """验证数据结构是否符合预期"""
        # 可根据具体需求实现详细的数据结构验证
        if not isinstance(data, type(schema)):
            return False
        if isinstance(data, dict):
            for key, value_type in schema.items():
                if key not in data or not isinstance(data[key], value_type):
                    return False
        return True