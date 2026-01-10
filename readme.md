# Vulmap - 优化版

Vulmap 是一款开源的远程漏洞扫描工具，支持多种漏洞类型扫描，包括 Apache-Shiro、Apache-Solr、Spring、Struts2、Tomcat、WebLogic、ThinkPHP、Drupal、ElasticSearch、Fastjson、Jenkins、Laravel、Nexus、JBoss、VMware 等多款中间件的漏洞检测。

## 🚀 主要特性

### 安全性增强
- **加密配置管理**: 使用 Fernet 加密算法安全存储敏感信息（API 密钥、认证凭据等）
- **输入验证**: 提供 URL、主机名、IP 地址等输入验证，防止路径穿越和注入攻击
- **安全编码实践**: 改进异常处理，避免敏感信息泄露

### 性能优化
- **动态线程池**: 根据系统资源自动调整线程数量，优化资源利用率
- **智能请求限速**: 实现自适应请求频率控制，避免对目标系统造成过大压力
- **资源监控**: 实时监控 CPU 和内存使用情况，动态调整扫描策略

### 架构改进
- **模块化设计**: 采用清晰的模块分离，提高代码可维护性
- **线程安全**: 全局变量管理采用线程安全机制，确保并发操作安全
- **类型安全**: 提供类型安全的全局变量访问接口

## 📦 新增模块说明

### common/config_manager.py
- `SecureConfigManager`: 安全配置管理器，使用加密存储敏感信息
- `AppConfig`: 应用配置类，提供安全的配置访问接口

### common/validators.py
- `InputValidator`: 输入验证器，验证URL、主机名、IP等
- 提供便捷函数进行输入验证和清理

### common/global_store.py (作为 module/globals.py)
- `ThreadSafeGlobalStore`: 线程安全的全局变量存储
- `TypedGlobalStore`: 类型安全的全局变量访问

### common/rate_limiter.py
- `RateLimiter`: 速率限制器，控制请求频率
- `AdaptiveRateLimiter`: 自适应速率限制器，根据响应情况调整
- `DelayManager`: 延迟管理器，提供智能延迟

### common/concurrent_manager.py
- `DynamicThreadPool`: 动态线程池，根据系统资源自动调整
- `TaskScheduler`: 任务调度器，提供高级调度功能

## 🔧 快速开始

### 安装要求
- Python 3.6+

### 依赖包
- gevent
- pycryptodome
- cryptography
- psutil

### 安装方法

#### 方法一：直接运行
```bash
git clone https://github.com/fyfhcgch/vulmap.git
cd vulmap
pip3 install -r requirements.txt
python3 vulmap.py --help
```

#### 方法二：Docker
```bash
git clone https://github.com/fyfhcgch/vulmap.git
cd vulmap
docker build -t vulmap .
docker run --rm -it vulmap --help
```

## ⚙️ 配置加密（重要）

首次使用前，请设置环境变量以启用安全配置管理：

```bash
# Linux/macOS
export VULMAP_CONFIG_PASSWORD="your_secure_password"

# Windows
set VULMAP_CONFIG_PASSWORD=your_secure_password
```

然后初始化安全配置（首次使用）：
```python
from common.config_manager import initialize_secure_config

# 初始化配置管理器
config = initialize_secure_config("your_secure_password")

# 设置敏感信息
config.set('fofa_email', 'your@email.com')
config.set('fofa_key', 'your_fofa_key')
config.set('shodan_key', 'your_shodan_key')
# ... 其他敏感配置
```

## 🛠️ 使用方法

### 基本用法
```bash
# 查看帮助信息
python3 vulmap.py --help

# 查看支持的漏洞列表
python3 vulmap.py --list

# 扫描单个URL
python3 vulmap.py -u "http://example.com"

# 批量扫描文件中的URL
python3 vulmap.py -f urls.txt

# 指定特定的应用进行扫描
python3 vulmap.py -u "http://example.com" -a struts2

# 使用FOFA API进行扫描
python3 vulmap.py --fofa "app=Apache-Shiro" --fofa-size 200

# 使用Shodan API进行扫描
python3 vulmap.py --shodan "Shiro"

# 自定义线程数
python3 vulmap.py -f urls.txt -a weblogic -t 20

# 导出结果到JSON文件
python3 vulmap.py -f urls.txt --output-json results.json

# 使用代理
python3 vulmap.py -u "http://example.com" --proxy-socks 127.0.0.1:1080
```

### 参数说明

#### 目标选项
- `-u, --url`: 指定目标URL (例如: -u "http://example.com")
- `-f, --file`: 指定目标列表文件 (例如: -f "list.txt")
- `--fofa`: 调用FOFA API进行扫描 (例如: --fofa "app=Apache-Shiro")
- `--shodan`: 调用Shodan API进行扫描 (例如: --shodan "Shiro")

#### 模式选项
- `-a`: 指定Web应用程序类型 (例如: -a "tomcat")，支持多个应用

#### 通用选项
- `-t, --thread`: 扫描线程数，默认10个线程
- `--dnslog`: DNSLOG服务器 (hyuga,dnslog,ceye)，默认自动选择
- `--output-text`: 结果导出到文本文件
- `--output-json`: 结果导出到JSON文件
- `--proxy-socks`: SOCKS代理 (例如: --proxy-socks 127.0.0.1:1080)
- `--proxy-http`: HTTP代理 (例如: --proxy-http 127.0.0.1:8080)
- `--fofa-size`: FOFA查询目标数量，默认100 (1-10000)
- `--user-agent`: 自定义用户代理
- `--delay`: 延迟检查时间，默认0秒
- `--timeout`: 扫描超时时间，默认10秒
- `--list`: 显示支持的漏洞列表
- `--debug`: 开启调试模式
- `--check`: 存活检查 (on/off)，默认on

## 🔍 支持的漏洞类型

Vulmap 支持检测以下漏洞类型（包括但不限于）：

- Apache ActiveMQ (CVE-2015-5254, CVE-2016-3088)
- Apache Druid (CVE-2021-25646)
- Apache Flink (CVE-2020-17518, CVE-2020-17519)
- Apache OFBiz (CVE-2021-26295, CVE-2021-29200, CVE-2021-30128)
- Apache Shiro (CVE-2016-4437)
- Apache Solr (CVE-2017-12629, CVE-2019-0193, CVE-2019-17558等)
- Apache Struts2 (多种S2漏洞)
- Apache Tomcat (CVE-2017-12615, CVE-2020-1938)
- Apache Unomi (CVE-2020-13942)
- CoreMail 配置信息泄露
- Drupal 漏洞 (CVE-2018-7600, CVE-2019-6340等)
- Ecology 工作流服务漏洞
- Elasticsearch 漏洞 (CVE-2014-3120, CVE-2015-1427)
- F5 BIG-IP (CVE-2020-5902)
- Fastjson 漏洞
- Exchange 漏洞
- 以及其他多种框架和系统的漏洞

## 🔐 配置API密钥

为了使用FOFA、Shodan和其他API功能，你需要配置安全的API密钥设置：

1. 设置环境变量：
```bash
export VULMAP_CONFIG_PASSWORD="your_secure_password"
```

2. 初始化安全配置：
```python
from common.config_manager import initialize_secure_config

config = initialize_secure_config("your_secure_password")
config.set('fofa_email', 'your@email.com')
config.set('fofa_key', 'your_fofa_key')
config.set('shodan_key', 'your_shodan_key')
# 保存配置
config.save_config()
```

## 📊 示例输出

```
                   __
                  [  |
  _   __  __   _   | |  _ .--..--.   ,--.  _ .--.
 [ \ [  ][  | | |  | | [ `.-. .-. | `'_\ :[ '/'`\ \
  \ \/ /  | \_/ |, | |  | | | | | | // | |,| \__/ |
   \__/   '.__.'_/[___][___||__||__]'-;__/| ;.___/
                                          [__|
[INFO] Start scanning target: http://example.com
[INFO] Scanning completed with no vulnerabilities found
```

## 📝 注意事项

⚠️ **免责声明**：
- 此工具仅供合法授权的企业安全建设活动使用
- 在使用此工具进行检测时，应确保行为符合当地法律法规并已获得足够授权
- 使用过程中存在任何非法行为，需自行承担相应后果，开发者不承担任何法律责任
- 使用前请仔细阅读并理解所有条款

## 📄 许可证

本项目采用 GNU General Public License v3.0 (GPL-3.0) 许可证。

## 👥 作者

- **原始作者**: zhzyker
- **优化版本**: fyfhcgch
- **GitHub**: https://github.com/fyfhcgch/vulmap
- **问题反馈**: https://github.com/fyfhcgch/vulmap/issues

## 🤝 贡献

欢迎提交Issue和Pull Request来改进此项目。

## 🎯 优化亮点

- **安全性**: 通过加密配置管理和输入验证显著提升安全性
- **性能**: 动态线程池和智能限速提高了扫描效率
- **稳定性**: 线程安全和类型安全增强了程序稳定性
- **易用性**: 模块化设计便于扩展和维护