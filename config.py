# -*- coding: utf-8 -*-

import pymysql

# vCenter 的的认证配置
VCCONFIG = {
    "Proenv-HL": {
        "vchost": "",
        "vcuser": "",
        "vcpassword": ""
    },
    "ProEnv-SSH": {
        "vchost": "",
        "vcuser": "",
        "vcpassword": ""
    },
    "ProEnv-ZZ": {
        "vchost": "",
        "vcuser": "",
        "vcpassword": ""
    },
}

# 虚拟机报表数据库类型
VM_DB_TYPE = "mysql"
# 虚拟机报表数据库连接字典
VM_DB_CONN_ARGS_MYSQL = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "zbx_record",
    "password": "",
    "db": "zbx_record",
    "charset": "utf8",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}
VM_DB_CONN_ARGS_PGSQL = {
}
VM_DB_CONN_ARGS = DB_CONN_ARGS_MYSQL

REGIST_DB_TYPE = VM_DB_TYPE
REGIST_DB_ARGS_MYSQL = {k: v for k, v in VM_DB_CONN_ARGS_MYSQL.items()}
# 由于使用的 group by 没有根据合适的分组方式，因此默认屏蔽掉 group by 的语法限制
REGIST_DB_ARGS_MYSQL["sql_mode"] = "STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION"
REGIST_DB_ARGS_PGSQL = {k: v for k, v in VM_DB_CONN_ARGS_PGSQL.items()}
REGIST_DB_ARGS = REGIST_DB_ARGS_PGSQL


# zabbix API 认证配置
ZBX_API_URL = "http://196.1.1.27/zabbix/api_jsonrpc.php"
ZBX_AUTH_USER = ""
ZBX_AUTH_PASSWORD = ""

# zabbix 服务器数据认证配置
ZBX_DB_TYPE = "postgresql"
ZBX_DB_ARGS_MYSQL = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "query",
    "password": "",
    "charset": "utf8",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}
ZBX_DB_ARGS_PGSQL = {
    
}
ZBX_DB_ARGS = ZBX_DB_ARGS_MYSQL


ZBX_DB_HOST = "127.0.0.1"
ZBX_DB_PORT = 3306
ZBX_DB_USER = "query"
ZBX_DB_PASSWORD = ""
ZBX_DB_SCHEMA = "zabbix"
ZBX_DB_CHARSET = "utf8"


# 对每个数据中心的 VC 的连接地址与别名对应
ZBX_PROXY_VC_MAPPING = {
    "196.1.1.101": "SSH",
    "180.18.225.101": "HL",
    "196.255.1.20": "ZZ",
}

# 每个 VC 对应的 zabbix proxy 成员
ZBX_PROXY_MEMBER = {
    "SSH": ["196.1.1.26"],
    "HL": ["180.18.225.218"],
    "ZZ": ["196.255.1.25"],
}

# 将虚拟机的操作系统对应各自在 zabbix 上的主机组
ZBX_SYS_GROUP_MAPPING = {
    "windows": ["Windows服务器"],
    "linux": ["Linux服务器"]
}

# zabbix 目前支持的 windows 操作系统
ZBX_SYSPREFIX_WIN = (
    "Microsoft Windows 10 (32 位)",
    "Microsoft Windows 10 (64 位)",
    "Microsoft Windows 2000",
    "Microsoft Windows 2000 Professional",
    "Microsoft Windows 7 (32 位)",
    "Microsoft Windows 7 (64 位)",
    "Microsoft Windows Server 2003 (32 位)",
    "Microsoft Windows Server 2003 (64 位)",
    "Microsoft Windows Server 2003 Standard (32 位)",
    "Microsoft Windows Server 2008 (32 位)",
    "Microsoft Windows Server 2008 (64 位)",
    "Microsoft Windows Server 2008 R2 (64 位)",
    "Microsoft Windows Server 2008 R2 (64-bit)",
    "Microsoft Windows Server 2012 (64 位)",
    "Microsoft Windows Server 2016 (64 位)",
    "Microsoft Windows XP Professional (32 位)",
)

# zabbix 目前支持的 Linux 操作系统
ZBX_SYSPREFIX_LNX = (
    "CentOS 4/5/6 (32 位)",
    "CentOS 4/5/6 (32-bit)",
    "CentOS 4/5/6/7 (64 位)",
    "CoreOS Linux (64 位)",
    "Other 3.x or later Linux (64-bit)",
    "Red Hat Enterprise Linux 3 (32 位)",
    "Red Hat Enterprise Linux 4 (32 位)",
    "Red Hat Enterprise Linux 5 (32 位)",
    "Red Hat Enterprise Linux 5 (64 位)",
    "Red Hat Enterprise Linux 6 (32 位)",
    "Red Hat Enterprise Linux 6 (64 位)",
    "Red Hat Enterprise Linux 7 (64 位)",
    "Red Hat Enterprise Linux 7 (64-bit)",
    "RHEL-server-7.2",
    "SUSE Linux Enterprise 10 (32 位)",
    "SUSE Linux Enterprise 11 (64 位)",
)

# zabbix 中根据添加的主机组来指定配置模板
ZBX_TEMPLATE_SYS_MAPPING = {
    "windows": ["DGB OS Windows"],
    "linux": ["DGB OS Linux", "DGB APP Monitor New"]
}