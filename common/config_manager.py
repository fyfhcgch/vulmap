#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全配置管理模块
提供加密存储和安全访问API密钥等敏感信息的功能
"""
import os
import json
import base64
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureConfigManager:
    """
    安全配置管理器
    使用加密技术保护敏感配置信息
    """
    
    def __init__(self, password: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            password: 用于加密/解密的密码，如果未提供则尝试从环境变量获取
        """
        self.password = password or os.getenv('VULMAP_CONFIG_PASSWORD', '')
        self.config_file = os.getenv('VULMAP_CONFIG_FILE', './config.secure')
        self._cipher_suite = None
        
        if not self.password:
            raise ValueError("必须提供密码用于加密/解密配置信息")
    
    @property
    def cipher_suite(self) -> Fernet:
        """获取加密套件实例"""
        if self._cipher_suite is None:
            # 从密码派生密钥
            password_bytes = self.password.encode()
            salt = b'salt_1234567890'  # 实际应用中应该使用随机盐值
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
            self._cipher_suite = Fernet(key)
        
        return self._cipher_suite
    
    def encrypt_data(self, data: str) -> str:
        """
        加密数据
        
        Args:
            data: 待加密的数据
            
        Returns:
            加密后的数据（Base64编码）
        """
        encrypted_bytes = self.cipher_suite.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        解密数据
        
        Args:
            encrypted_data: 已加密的数据（Base64编码）
            
        Returns:
            解密后的原始数据
        """
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    
    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """
        保存配置到加密文件
        
        Args:
            config_data: 配置数据字典
            
        Returns:
            保存是否成功
        """
        try:
            # 加密配置数据
            json_data = json.dumps(config_data)
            encrypted_data = self.encrypt_data(json_data)
            
            # 写入文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            
            # 设置文件权限（仅所有者可读写）
            os.chmod(self.config_file, 0o600)
            
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        从加密文件加载配置
        
        Returns:
            配置数据字典，如果失败返回None
        """
        if not os.path.exists(self.config_file):
            return None
        
        try:
            # 读取加密数据
            with open(self.config_file, 'r', encoding='utf-8') as f:
                encrypted_data = f.read()
            
            # 解密数据
            json_data = self.decrypt_data(encrypted_data)
            config_data = json.loads(json_data)
            
            return config_data
        except Exception as e:
            print(f"加载配置失败: {e}")
            return None
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        config = self.load_config()
        if config and key in config:
            return config[key]
        return default
    
    def set_config_value(self, key: str, value: Any) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            设置是否成功
        """
        config = self.load_config() or {}
        config[key] = value
        return self.save_config(config)


class AppConfig:
    """
    应用配置类
    提供安全的配置访问接口
    """
    
    def __init__(self, config_manager: SecureConfigManager):
        self.config_manager = config_manager
        self._default_values = {
            'UA': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'TIMEOUT': 10,
            'THREADNUM': 10,
            'DELAY': 0,
            'VULMAP': '0.9',
            'O_TEXT': None,
            'O_JSON': None,
            'CHECK': 'on',
            'DEBUG': False,
            'DNSLOG': 'auto',
            'ceye_domain': '',
            'ceye_token': '',
            'hyuga_domain': '',
            'hyuga_token': '',
            'fofa_email': '',
            'fofa_key': '',
            'shodan_key': ''
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，优先从加密配置文件读取，其次使用默认值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        # 首先尝试从加密配置文件读取
        value = self.config_manager.get_config_value(key)
        if value is not None:
            return value
        
        # 其次尝试从环境变量读取
        env_key = f'VULMAP_{key.upper()}'
        env_value = os.getenv(env_key)
        if env_value is not None:
            # 尝试转换类型
            default_value = self._default_values.get(key, default)
            if isinstance(default_value, int):
                try:
                    return int(env_value)
                except ValueError:
                    return default_value
            elif isinstance(default_value, bool):
                return env_value.lower() in ('true', '1', 'yes', 'on')
            else:
                return env_value
        
        # 最后返回默认值
        return self._default_values.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值到加密配置文件
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            设置是否成功
        """
        return self.config_manager.set_config_value(key, value)


def initialize_secure_config(password: str = None) -> AppConfig:
    """
    初始化安全配置系统
    
    Args:
        password: 加密密码
        
    Returns:
        配置对象
    """
    if not password:
        password = os.getenv('VULMAP_CONFIG_PASSWORD')
        if not password:
            raise ValueError("请设置VULMAP_CONFIG_PASSWORD环境变量或提供密码")
    
    config_manager = SecureConfigManager(password)
    return AppConfig(config_manager)


# 便捷函数
def get_config_value(key: str, default: Any = None) -> Any:
    """
    便捷函数：获取配置值
    注意：这会使用默认密码（来自环境变量）
    """
    try:
        password = os.getenv('VULMAP_CONFIG_PASSWORD', 'default_password_for_demo')
        app_config = initialize_secure_config(password)
        return app_config.get(key, default)
    except:
        # 如果加密配置不可用，回退到原始方式
        import module.globals as globals_module
        return globals_module.get_value(key, default)


def set_config_value(key: str, value: Any) -> bool:
    """
    便捷函数：设置配置值
    注意：这会使用默认密码（来自环境变量）
    """
    try:
        password = os.getenv('VULMAP_CONFIG_PASSWORD', 'default_password_for_demo')
        app_config = initialize_secure_config(password)
        return app_config.set(key, value)
    except:
        # 如果加密配置不可用，回退到原始方式
        import module.globals as globals_module
        globals_module.set_value(key, value)
        return True