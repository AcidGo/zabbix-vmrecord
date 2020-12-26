# Author: AcidGo

import logging
import random
import re
import time

from config import *
from datetime import datetime
from pyzabbix import ZabbixAPI
from reporter import VMReport
from sqlalchemy import and_, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

class ZBXWorker(object):
    """执行 Zabbix 相关工作。
    """

    def __init__(self):
        self._zbx_api = None
        self._hosts_created = {}

    def zbx_login(self, host, **kwargs):
        """
        """
        self._zbx_api = ZabbixAPI(host)
        self._zbx_api.login(**kwargs)

    def reset_host_created(self):
        """
        """
        self._hosts_created = {}

    def create_host(
        self, 
        host_name,
        visible_name,
        group_lst,
        agent_interface_ip,
        agent_interface_port,
        proxy,
        enabled,
        template_lst):
        """
        """
        groupid_lst =  self._zbx_api.hostgroup.get(
                output = ["groupid"], 
                filter = {"name": group_lst},
        )
        templateid_lst = self._zbx_api.template.get(
                output = ["templateid"],
                filter = {"host": template_lst},
        )
        proxyid_lst = self._zbx_api.proxy.get(
            output = ["proxyid"],
            filter = {"host": proxy}
        )
        proxy_hostid = proxyid_lst[0] if len(proxyid_lst) > 0 else None

        res = self._zbx_api.host.create(
            host = host_name,
            name = visible_name,
            groups = groupid_lst,
            interfaces = {
                "type": 1,
                "main": 1,
                "useip": 1,
                "dns": "",
                "ip": agent_interface_ip,
                "port": str(agent_interface_port),
            },
            templates = templateid_lst,
            proxy_hostid = proxy_hostid,
            status = str(enabled)
        )
        self._hosts_created[host_name] = res["hostids"]

    def create_hosts(self, data_lst):
        """
        """
        self.reset_host_created()
        for data in data_lst:
            self.create_host(**data)
            time.sleep(0.2)
        self.maintenance()

    def maintenance(self):
        """
        """
        hostid_set = set()
        for k, v in self._hosts_created.items():
            for i in v:
                hostid_set.add(i)
        if not hostid_set:
            logging.info("empty hostids to create maintenance, nothing to do")
            return

        maintenance_name = datetime.now().strftime("%Y%m%d") + "-{!s}-{!s}".format(__file__.rsplit(".", 1)[0], random.randint(1000,9999))
        # hard-core setting for 3 hours
        maintenance_period = 60*60*3
        self._zbx_api.maintenance.create(
            name = maintenance_name,
            hostids = list(hostid_set),
            active_since = int(time.time()),
            active_till = int(time.time()) + maintenance_period,
            timeperiods = [
                {
                    "timeperiod_type": 0,
                    # older 300 seconds
                    "start_date": int(time.time()) - 300,
                    "period": maintenance_period,
                },
            ]
        )

    def get_all_host(self):
        """
        """
        esists_host_lst = [i["host"] for i in self._zbx_api.host.get(output = ["host"])]
        return esists_host_lst

class Register(ZBXWorker):
    def collect(self):
        raise Exception("please overwrite me")
    def registe(self):
        raise Exception("please overwrite me")

class DBRegister(Register):
    """
    """
    valid_period_days = 30
    re_p_ip = re.compile(r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$")

    def __init__(self):
        super(DBRegister, self).__init__()
        self._filter = []
        self._db_session = None
        self._data = None

    def collect(self):
        if self._db_session is None:
            raise Exception("not found mysql conn for reporting data")
        latest_create_time = self._db_session.query(func.max(VMReport.create_time)).scalar()
        # 有效期限
        if (datetime.now() - latest_create_time).total_seconds() > self.valid_period_days*(60*60*24):
            logging.warning(f"the latest create time earlier than {self.valid_period_days} days")
            self.set_data(None)
        rows = self._db_session.query(VMReport).filter(VMReport.create_time==latest_create_time).filter(VMReport.vm_powerstate=="poweredOn").all()
        logging.info(f"collect {len(rows)} vms info from the database")

        res = []
        for row in rows:
            res_cooked = self._cook(row)
            if res_cooked:
                res.append(res_cooked)
        self.set_data(res)

    def registe(self):
        if not self.get_data():
            logging.warning("the data collected is empty, nothing to do")
            return
        self.create_hosts(self.get_data())

    def _cook(self, row):
        """
        """
        res_meta = {
            "host_name": None,
            "visible_name": None,
            "group_lst": None,
            "agent_interface_ip": None,
            "agent_interface_port": None,
            "proxy": None,
            "enabled": None,
            "template_lst": None
        }

        if len(row.vm_netinfo) > 0:
            ip_lst = list(set([v for v in row.vm_netinfo.values()]))
        else:
            ip_lst = []

        # 1. 确定主机名称
        # 1.1 仅有一个 IP，则设置为主机名称
        if len(ip_lst) == 1:
            res_meta["host_name"] = ip_lst[0]
        # 1.2 有多个 IP，则选取与虚拟机名近似的 IP 作为主机名称
        elif len(ip_lst) > 1:
            for i in ip_lst:
                # very simple method, fix me
                if i in row.vm_name:
                    res_meta["host_name"] = i
                    break
            else:
                logging.error(f"failed to get the host_name from the row, the vm {row.vm_name} and ip_lst {ip_lst} maybe not good")
                return
        # 1.3 没有 IP，且虚拟机名符合 IP 规范，则将虚拟机设置为主机名称
        else:
            # very simple, fix me
            if row.vm_name.count(".") == 3:
                logging.info(f"not found the ip from {row.vm_name}, but use the name of vm for ip")
                res_meta["host_name"] = row.vm_name
            else:
                logging.error(f"failed to get the host_name from the row, the vm {row.vm_name} and ip_lst {ip_lst} maybe not good")
                return
        # 1.4 如果确定的 IP 在过滤清单中，则过滤
        if res_meta["host_name"] in self._filter:
            logging.debug("the ip {!s} has be filter".format(res_meta["host_name"]))
            return

        # 2. 确定 Agent Proxy
        # 可以根据不同机房布局和容灾配置来分配选择函数
        try:
            res_meta["proxy"] = self._select_proxy(row)
        except Exception as e:
            logging.error("cannot find the specifial zabbix proxy: {!s}".format(e))
            return

        # 3 设置为创建立即使用
        res_meta["enabled"] = 0

        # 4. 通过主机名称确定 agent 的接口监听
        if res_meta["host_name"]:
            res_meta["agent_interface_ip"] = res_meta["host_name"]
            # 默认使用 10050 端口
            res_meta["agent_interface_port"] = 10050
        else:
            logging.error("cannot found agent listen port, the vm is: {s}.".format(row.vm_name))
            return
        if not self.re_p_ip.search(res_meta["agent_interface_ip"]):
            logging.error("the agent_interface_ip is not a ip format: {s}".format(res_meta["agent_interface_ip"]))
            return 

        # 5. 确定模板和主机群组
        try:
            sys_type, res_meta["group_lst"], res_meta["template_lst"] = self._select_group_template(row)
        except Exception as e:
            logging.error("cannot find the group and template on zabbix: {!s}".format(e))
            return

        # 6. 设置可见名称
        # 6.1 如果虚拟机备注可用，则将备注作为课件内容的中间内容
        if row.vm_annotation.strip():
            prefix = "LNX" if sys_type == ZBX_SYSTYPE_LNX else "WIN"
            res_meta["visible_name"] = "{!s}_{!s}_{!s}".format(prefix, row.vm_annotation, res_meta["agent_interface_ip"])
        # 6.2 如果虚拟机备注不可用，则这里选择报错，标准化啦，这里不填坑了
        else:
            logging.error(f"not found the vm_annotation on vm {row.vm_name}.")
            return

        return res_meta

    def db_login(self, db_urls):
        """
        """
        # engine = create_engine(db_urls, echo=True)
        engine = create_engine(db_urls)
        Base.metadata.create_all(engine)
        self._db_session = sessionmaker(engine)()
        logging.info("initializing database session is finished")

    def set_data(self, data):
        self._data = data

    def get_data(self):
        return self._data

    def set_filter(self, filter):
        self._filter = filter

    def _select_proxy(self, row):
        return ZBX_PROXY_MEMBER[ZBX_PROXY_VC_MAPPING[row.vm_vcenter_ip]]

    def _select_group_template(self, row):
        sys_type = None
        if row.vm_guestfullname in ZBX_SYSPREFIX_WIN:
            sys_type = ZBX_SYSTYPE_WIN
        elif row.vm_guestfullname in ZBX_SYSPREFIX_LNX:
            sys_type = ZBX_SYSTYPE_LNX
        else:
            logging.error("Cannot find the OS(vm_guestfullname) on the vm {s}.".format(row.vm_name))
            raise Exception()
        return sys_type, ZBX_SYS_GROUP_MAPPING[sys_type], ZBX_TEMPLATE_SYS_MAPPING[sys_type]

def init_logger(level, logfile=None):
    """日志功能初始化。
    如果使用日志文件记录，那么则默认使用 RotatinFileHandler 的大小轮询方式，
    默认每个最大 10 MB，最多保留 5 个。
    Args:
        level: 设定的最低日志级别。
        logfile: 设置日志文件路径，如果不设置则表示将日志输出于标准输出。
    """
    import os
    import sys
    if not logfile:
        logging.basicConfig(
            level = getattr(logging, level.upper()),
            format = "%(asctime)s [%(levelname)s] %(message)s",
            datefmt = "%Y-%m-%d %H:%M:%S"
        )
    else:
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, level.upper()))
        if logfile.lower() == "local":
            logfile = os.path.join(sys.path[0], os.path.basename(os.path.splitext(__file__)[0]) + ".log")
        handler = RotatingFileHandler(logfile, maxBytes=10*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logging.info("Logger init finished.")

if __name__ == "__main__":
    init_logger("info")
    try:
        register = DBRegister()
        register.zbx_login(ZBX_HOST, **ZBX_LOGIN_ARGS)
        register.db_login(REPORT_DB_URLS)
        filter = register.get_all_host()
        register.set_filter(filter)
        register.collect()
        register.registe()
    except Exception as e:
        logging.exception(e)
        exit(1)