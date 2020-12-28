## zabbix-vmrecord

从 VMware vSphere vCenter/ESXi 登记录入虚拟机信息，持久化相关数据到后端存储，在需要制定报表统计时可由其供数。此外，可以把最新的虚拟机统计信息自动注册到 Zabbix 监控主机，并能为此批新增主机拉入维护窗口，避免未知情况扰乱告警系统。

### 配置

主要配置文件为同级目录下的 config.py，特殊或底层配置需要在源码中修改，如 virtualmachine properties view。

```python
# 后端数据的 url，供 sqlalchemy 使用，可依据实际情况来选择数据库类型
# 此传参并不是保证注册 Zabbix 的必要条件，可以选择用 pipeline 将上报和注册的 collect 连接起来，则不需要中间库
REPORT_DB_URLS = "postgresql+psycopg2://zabbix:zabbix@10.10.31.153:5432/zabbix"

# 是否需要将新创建主机加入维护模式
# 如果选择否，那么必须承担初次加入监控的主机的未知状态，可能导致告警风暴
ZBX_MAINTENANCE_FOR_CREATED = True

# vCenter 的的认证配置
# 可配置多套 vCenter 地址，key 为此 vCenter 的别名，value 为连接的实际参数
VCCONFIG = {
    "Testenv-A": {
        "host": "10.10.10.39",
        "user": "",
        "pwd": ""
    },
}

# Zabbix API 登录信息
ZBX_HOST = "http://10.10.32.35/zabbix/api_jsonrpc.php"
ZBX_LOGIN_ARGS = {
    "user": "Admin",
    "password": "zabbix",
}

# 每个 vCenter 对应的 Zabbix Proxy 成员
# 内部环境是多机房多分区的架构，因此不同 vCenter 所在区域可能需要对接特定的 agent 代理，可在此配置
ZBX_PROXY_MEMBER = {
    "Testenv-A": ["10.10.32.44"],
}

# 每个 vCenter 对应的 Zabbix Proxy 成员
# 主要为了方便从 vCenter 的连接地址定位到 vCenter 标签，如果使用 IP 登录则保持默认格式，如果使用 FQDN 则可定制配置
ZBX_PROXY_VC_MAPPING = {v["host"]: k for k, v in VCCONFIG.items()}

# 操作系统简称类别命名
# 为了能够在代码内分类虚拟机的操作系统而设置的常量，必须保证与 ZBX_SYS_GROUP_MAPPING 和 ZBX_TEMPLATE_SYS_MAPPING 的 key 一致
ZBX_SYSTYPE_WIN = "windows"
ZBX_SYSTYPE_LNX = "linux"

# 根据虚拟机的操作系统来附加至 Zabbix 中的主机群组
ZBX_SYS_GROUP_MAPPING = {
    ZBX_SYSTYPE_WIN: ["Windows服务器"],
    ZBX_SYSTYPE_LNX: ["Linux服务器"]
}

# Zabbix 中根据添加的主机组来指定配置模板
ZBX_TEMPLATE_SYS_MAPPING = {
    ZBX_SYSTYPE_WIN: ["Template OS Windows"],
    ZBX_SYSTYPE_LNX: ["Template OS Linux", "APP Monitor New"]
}

# vCenter 显示的系统中，Zabbix 目前支持的 Windows 操作系统，来自 vSphere 6.0+
# 如需屏蔽某操作系统支持，可将其从中删除，但需要注意，虚拟机的操作系统由 vSphere Guest 获取，不一定完全准确
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
    "Microsoft Windows Server 2016 或更高版本 (64 位)",
    "Microsoft Windows XP Professional (32 位)",
)

# vCenter 显示的系统中，Zabbix 目前支持的 Linux 操作系统，来自 vSphere 6.0+
# 如需屏蔽某操作系统支持，可将其从中删除，但需要注意，虚拟机的操作系统由 vSphere Guest 获取，不一定完全准确
ZBX_SYSPREFIX_LNX = (
    "CentOS 4/5 或更高版本 (32 位)",
    "CentOS 4/5 或更高版本 (64 位)",
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
```

### 使用

+ reporter.py

  负责从 vCenter/ESXi 中收集指定虚拟机属性，并将数据上报。

  虚拟机收集功能由 `VMWorker` 实现，通过 `vm_properties` 预定义的虚拟机属性来规划搜索视图，来检索全部虚拟机。

  ORM 映射类中定义了持久化的数据结构，内部有字段定义的详细的注释可供参考。

+ register.py

  负责从 reporter 上报的数据中筛选过滤合适的虚拟机条目，通过 API 与 Zabbix 交互将符合条件的主机根据既定配置进行注册。

### 拓展

作者内部对虚拟机和 Zabbix 的注册需求较简单，目前也不太想持续维护，如下有工具拓展的建议。

+ 虚拟机属性扩展

  内部依据搜索试图的方式来检索虚拟机，可以简单地修改注入的属性列表来缩减或扩张虚拟机的搜集属性：

  ```python
  class VMWorker(object):
  	# ......
      vm_properties = [
          "config.instanceUuid",
          "name",
          "config.guestFullName",
          "config.annotation",
          "customValue",
          "runtime.host",
          "datastore",
          "config.uuid",
          "guest.net",
          "runtime.powerState",
          "guest.toolsStatus",
          "guest.hostName",
          "config.hardware.memoryMB",
          "config.hardware.numCPU",
          "config.hardware.numCoresPerSocket",
          "runtime.bootTime",
          "config.modified",
          "config.cpuHotAddEnabled",
          "config.memoryHotAddEnabled",
          "runtime.dasVmProtection",
          "storage.perDatastoreUsage",
      ]
  ```

+ 持久化类型修改

  工具通过 ORM 实现了对接数据库上报的 `DBReporter` ，如有其他持久化类型或上报规则，可实现 `Reporter` 中的接口要求即可。

+ 注册 Zabbix 主机规则

  作者内部的 Zabbix 主机有一定的规范要求，因此针对地实现了 `DBRegister._cook` 来满足，如不同环境有不同的规范可重写此方法。



