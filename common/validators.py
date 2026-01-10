#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入验证模块
提供对目标URL和其他输入参数的安全验证功能
"""
import re
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Union, Optional


class InputValidator:
    """
    输入验证器
    提供各种输入验证功能
    """
    
    # URL验证正则表达式
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'  # domain
        r'(?::\d{2,5})?'  # optional port
        r'(?:/.*)?$',  # optional path
        re.IGNORECASE
    )
    
    # IP地址验证正则表达式
    IP_PATTERN = re.compile(
        r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )
    
    # 域名验证正则表达式
    DOMAIN_PATTERN = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$',
        re.IGNORECASE
    )
    
    def __init__(self, allow_private_ips: bool = False, allow_local_hosts: bool = False):
        """
        初始化验证器
        
        Args:
            allow_private_ips: 是否允许私有IP地址
            allow_local_hosts: 是否允许本地主机（localhost, 127.0.0.1等）
        """
        self.allow_private_ips = allow_private_ips
        self.allow_local_hosts = allow_local_hosts
    
    def validate_url(self, url: str) -> bool:
        """
        验证URL格式
        
        Args:
            url: 待验证的URL
            
        Returns:
            验证是否通过
        """
        if not url or not isinstance(url, str):
            return False
        
        # 基本格式验证
        if not self.URL_PATTERN.match(url.strip()):
            return False
        
        try:
            parsed = urlparse(url.strip())
            
            # 验证协议
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # 验证主机名
            hostname = parsed.hostname
            if not hostname:
                return False
            
            # 检查是否是私有IP或本地主机
            if self._is_private_or_local_ip(hostname):
                if not self.allow_local_hosts and self._is_local_host(hostname):
                    return False
                if not self.allow_private_ips and self._is_private_ip(hostname) and not self._is_local_host(hostname):
                    return False
            
            # 检查是否包含危险字符或路径穿越
            if self._has_dangerous_characters(parsed.path or ''):
                return False
                
            return True
        except Exception:
            return False
    
    def validate_hostname(self, hostname: str) -> bool:
        """
        验证主机名
        
        Args:
            hostname: 待验证的主机名
            
        Returns:
            验证是否通过
        """
        if not hostname or not isinstance(hostname, str):
            return False
        
        hostname = hostname.strip()
        
        # 长度检查
        if len(hostname) > 253:
            return False
        
        # 域名格式验证
        if self.DOMAIN_PATTERN.match(hostname):
            return True
        
        # IP地址格式验证
        if self.IP_PATTERN.match(hostname):
            # 检查是否允许私有IP
            if not self.allow_private_ips and self._is_private_ip(hostname):
                return False
            if not self.allow_local_hosts and self._is_local_host(hostname):
                return False
            return True
        
        return False
    
    def validate_ip(self, ip: str) -> bool:
        """
        验证IP地址
        
        Args:
            ip: 待验证的IP地址
            
        Returns:
            验证是否通过
        """
        if not ip or not isinstance(ip, str):
            return False
        
        try:
            ip_obj = ipaddress.ip_address(ip.strip())
            
            # 检查是否允许私有IP
            if not self.allow_private_ips and ip_obj.is_private and not ip_obj.is_loopback:
                return False
            
            # 检查是否允许本地主机
            if not self.allow_local_hosts and ip_obj.is_loopback:
                return False
            
            return True
        except ValueError:
            return False
    
    def validate_port(self, port: Union[int, str]) -> bool:
        """
        验证端口号
        
        Args:
            port: 待验证的端口号
            
        Returns:
            验证是否通过
        """
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False
    
    def sanitize_input(self, input_str: str, max_length: int = 1000) -> str:
        """
        清理输入字符串，移除潜在的危险字符
        
        Args:
            input_str: 输入字符串
            max_length: 最大长度限制
            
        Returns:
            清理后的字符串
        """
        if not input_str:
            return ""
        
        # 截断过长的字符串
        input_str = input_str[:max_length]
        
        # 移除控制字符
        sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')
        
        # 移除潜在的危险模式
        dangerous_patterns = [
            r'\.\.',  # 路径穿越
            r'<script',  # XSS
            r'javascript:',  # JavaScript
            r'vbscript:',  # VBScript
            r'on\w+\s*=',  # 事件处理器
        ]
        
        for pattern in dangerous_patterns:
            import re
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    def _is_private_ip(self, host: str) -> bool:
        """
        检查是否为私有IP地址
        
        Args:
            host: 主机名或IP地址
            
        Returns:
            是否为私有IP
        """
        try:
            ip_obj = ipaddress.ip_address(host)
            return ip_obj.is_private and not ip_obj.is_loopback
        except ValueError:
            # 如果不是有效的IP地址，则尝试解析域名
            try:
                ip_addr = socket.gethostbyname(host)
                ip_obj = ipaddress.ip_address(ip_addr)
                return ip_obj.is_private and not ip_obj.is_loopback
            except:
                return False
    
    def _is_local_host(self, host: str) -> bool:
        """
        检查是否为本地主机
        
        Args:
            host: 主机名或IP地址
            
        Returns:
            是否为本地主机
        """
        local_hosts = ['localhost', '127.0.0.1', '::1', '0.0.0.0']
        if host.lower() in local_hosts:
            return True
        
        try:
            ip_obj = ipaddress.ip_address(host)
            return ip_obj.is_loopback
        except ValueError:
            return False
    
    def _is_private_or_local_ip(self, host: str) -> bool:
        """
        检查是否为私有或本地IP地址
        
        Args:
            host: 主机名或IP地址
            
        Returns:
            是否为私有或本地IP
        """
        try:
            ip_obj = ipaddress.ip_address(host)
            return ip_obj.is_private
        except ValueError:
            # 如果不是有效的IP地址，则尝试解析域名
            try:
                ip_addr = socket.gethostbyname(host)
                ip_obj = ipaddress.ip_address(ip_addr)
                return ip_obj.is_private
            except:
                return False
    
    def _has_dangerous_characters(self, path: str) -> bool:
        """
        检查路径中是否包含危险字符
        
        Args:
            path: URL路径
            
        Returns:
            是否包含危险字符
        """
        dangerous_patterns = [
            r'\.\./',  # 路径穿越
            r'%2e%2e%2f',  # URL编码的路径穿越
            r'\.\.\\',  # Windows路径穿越
            r'%2e%2e%5c',  # URL编码的Windows路径穿越
        ]
        
        path_lower = path.lower()
        for pattern in dangerous_patterns:
            import re
            if re.search(pattern, path_lower):
                return True
        
        return False


def validate_target_url(url: str, allow_private: bool = False, allow_local: bool = False) -> bool:
    """
    便捷函数：验证目标URL
    
    Args:
        url: 待验证的URL
        allow_private: 是否允许私有IP
        allow_local: 是否允许本地主机
        
    Returns:
        验证是否通过
    """
    validator = InputValidator(allow_private_ips=allow_private, allow_local_hosts=allow_local)
    return validator.validate_url(url)


def sanitize_user_input(input_str: str) -> str:
    """
    便捷函数：清理用户输入
    
    Args:
        input_str: 用户输入字符串
        
    Returns:
        清理后的字符串
    """
    validator = InputValidator()
    return validator.sanitize_input(input_str)