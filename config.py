# 上报的数据库源
# REPORT_DB_URLS = "mysql+pymysql://vm:abcd1234@192.168.66.31:3308/vm"
REPORT_DB_URLS = "postgresql+psycopg2://vm:abcd1234@192.168.66.31:5432/vm"

# vCenter 的的认证配置
VCCONFIG = {
    "Proenv-A": {
        "host": "",
        "user": "",
        "pwd": ""
    },
    "ProEnv-B": {
        "host": "",
        "user": "",
        "pwd": ""
    },
    "ProEnv-C": {
        "host": "",
        "user": "",
        "pwd": ""
    },
}

# Zabbix API 登录信息
ZBX_HOST = "http://192.168.66.50"
ZBX_LOGIN_ARGS = {
    "user": "Admin",
    "password": "zabbix",
}

# 每个 VC 对应的 zabbix proxy 成员
ZBX_PROXY_MEMBER = {
    "A": ["192.168.66.27", "192.168.66.28"],
    "B": ["192.168.67.27"],
    "C": ["192.168.68.27"],
}

# 每个 VC 对应的 zabbix proxy 成员
ZBX_PROXY_VC_MAPPING = {
    "196.1.1.1": "A",
    "196.1.1.2": "B",
    "196.1.1.3": "C",
}

# 操作系统简称类别命名
ZBX_SYSTYPE_WIN = "windows"
ZBX_SYSTYPE_LNX = "linux"

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
    "windows": ["Template OS Windows by Zabbix agent"],
    "linux": ["Template OS Linux by Zabbix agent"]
}