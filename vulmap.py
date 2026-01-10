#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author: zhzyker
# github: https://github.com/zhzyker/vulmap
# If you have any problems, please give feedback to https://github.com/zhzyker/vulmap/issues
from module.banner import banner
print(banner())  # 显示随机banner
from module.install import require
require()
from module.allcheck import version_check
from common.config_manager import initialize_secure_config, get_config_value
from common.validators import validate_target_url, sanitize_user_input
from common.global_store import init as global_init, set_value, get_value
from common.rate_limiter import wait_before_request, report_request_result
from common.concurrent_manager import submit_task, get_optimal_thread_count
from module import globals
from module.argparse import arg
from module.license import vulmap_license
from core.core import core
from module.time import now
from module.color import color
from thirdparty import urllib3

urllib3.disable_warnings()


def config():
    header = {
        'Accept': 'application/x-shockwave-flash, image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, '
                  'application/vnd.ms-excel, application/vnd.ms-powerpoint, application/msword, */*',
        'User-agent': get_value('UA'),
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'close'
    }
    global_init()  # 初始化全局变量模块
    set_value("UA", get_value('UA'))  # 设置全局变量UA
    set_value("VUL", get_value('VUL', None))  # 设置全局变量VULN用于判断是否漏洞利用模式
    set_value("CHECK", get_value('CHECK', 'on'))  # 目标存活检测
    set_value("DEBUG", get_value('DEBUG', False))  # 设置全局变量DEBUG
    set_value("DELAY", get_value('DELAY', 0))  # 设置全局变量延时时间DELAY
    set_value("DNSLOG", get_value('DNSLOG', 'auto'))  # 用于判断使用哪个dnslog平台
    set_value("DISMAP", get_value('DISMAP', 'false')) # 是否接收dismap识别结果(false/true)
    set_value("VULMAP", get_value('VULMAP', '0.9'))  # 设置全局变量程序版本号
    set_value("O_TEXT", get_value('O_TEXT', None))  # 设置全局变量OUTPUT判断是否输出TEXT
    set_value("O_JSON", get_value('O_JSON', None))  # 设置全局变量OUTPUT判断是否输出JSON
    set_value("HEADERS", header)  # 设置全局变量HEADERS
    set_value("TIMEOUT", get_value('TIMEOUT', 10))  # 设置全局变量超时时间TOMEOUT
    set_value("THREADNUM", get_value('THREADNUM', 10))  # 设置全局变量THREADNUM传递线程数量

    # 从安全配置中获取敏感信息
    set_value("ceye_domain", get_value('ceye_domain', ''))
    set_value("ceye_token", get_value('ceye_token', ''))

    # 替换自己的 http://hyuga.co 的域名和 token
    set_value("hyuga_domain", get_value('hyuga_domain', ''))
    set_value("hyuga_token", get_value('hyuga_token', ''))

    # fofa 邮箱和 key，需要手动修改为自己的
    set_value("fofa_email", get_value('fofa_email', ''))
    set_value("fofa_key", get_value('fofa_key', ''))

    # shodan key
    set_value("shodan_key", get_value('shodan_key', ''))


if __name__ == '__main__':
    try:
        vulmap_license() # vulmap 用户协议及免责声明
        args = arg()  # 初始化各选项参数
        
        # 验证输入参数
        if args.url:
            validated = validate_target_url(args.url, allow_private=False, allow_local=False)
            if not validated:
                print(now.timed(de=0) + color.red_warn() + color.red(" Invalid target URL: " + args.url))
                exit(0)
            # 清理输入
            args.url = sanitize_user_input(args.url)
        
        if args.file:
            # 这里可以添加对文件路径的验证
            pass
        
        config()  # 加载全局变量
        version_check()  # 检查vulmap版本
        
        # 根据系统资源优化线程数
        optimal_threads = get_optimal_thread_count(get_value('THREADNUM', 10))
        set_value("THREADNUM", optimal_threads)
        
        if optimal_threads != get_value('THREADNUM', 10):
            print(now.timed(de=0) + color.yel_info() + color.yellow(
                f" Adjusted thread number to {optimal_threads} based on system resources"))
        
        core.control_options(args)  # 运行核心选项控制方法用于处理不同选项并开始扫描
    except KeyboardInterrupt as e:
        print(now.timed(de=0) + color.red_warn() + color.red(" Stop scanning"))
        exit(0)
    except Exception as e:
        print(now.timed(de=0) + color.red_warn() + color.red(f" Unexpected error: {str(e)}"))
        exit(1)