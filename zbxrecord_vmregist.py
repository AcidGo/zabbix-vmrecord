# -*- coding: utf-8 -*-
# Author: AcidGo


import atexit
import json
import re
import logging
import time
import psycopg2
import pymysql
from urllib.request import Request, urlopen


class ZBXApi(object):
    def __init__(self, url, user, passwd):
        self.url = url
        self.user = user
        self.passwd = passwd
        self.auth_id = 1
        self.auth_token = None
        self.host_created = {}

        self._auth()

    def _zbx_request(self, data_dct):
        """
        """
        data_json = json.dumps(data_dct).encode("utf-8")
        request = Request(self.url, data=data_json)
        request.add_header("Content-Type", "application/json")
        try:
            response = urlopen(request, timeout=5)
            res_json = response.read().decode("utf-8")
            response.close()
            return res_json
        except Exception as e:
            logging.error("Get error when request to {!s}: {!s}".format(self.url, e))
            raise e

    def _auth(self):
        """
        """
        data = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "user": self.user,
                "password": self.passwd
            },
            "id": self.auth_id
        }
        res = self._zbx_request(data)
        res = json.loads(res)
        if "result" not in res:
            logging.error("Auth failed, not found result in response: {!s}".format(res))
            raise ValueError
        self.auth_token = res["result"]
        return res["result"]

    def create_host_some(self, data_lst):
        """
        """
        for data in data_lst:
            self.create_host_once(**data)
            time.sleep(0.1)
        self.maintenance()

    def create_host_once(self, 
        host_name,
        visible_name,
        group_lst,
        agent_interface_ip,
        agent_interface_port,
        proxy,
        enabled,
        template_lst
        ):
        """
        """
        groupid_lst = [{"groupid": i} for i in self.get_groups(group_lst)]
        templateid_lst = [{"templateid": i} for i in self.get_templates(template_lst)]
        t = self.get_proxyid(proxy)
        proxy_hostid = t[0] if t else None

        data = {
            "jsonrpc": "2.0",
            "method": "host.create",
            "params":
                {
                    "host": host_name,
                    "name": visible_name,
                    "groups": groupid_lst,
                    "interfaces": {
                        "type": 1,
                        "main": 1,
                        "useip": 1,
                        "dns": "",
                        "ip": agent_interface_ip,
                        "port": str(agent_interface_port)
                    },
                    "templates": templateid_lst,
                    "proxy_hostid": proxy_hostid,
                    "status": str(enabled)
                },
            "auth": self.auth_token,
            "id": self.auth_id
        }
        logging.debug("The create host data:")
        logging.debug(str(data))

        res = self._zbx_request(data)
        res = json.loads(res)
        if "error" in res:
            logging.error("Create host is fialed: {!s}".format(res["error"]))
        elif "result" in res:
            logging.info("Create host is good: {!s}".format(res["result"]))
            if "hostids" in res["result"]:
                self.host_created[host_name] = res["result"]["hostids"]
            return res["result"]
        else:
            logging.error("Create host trigger a UNKNOW error: {0!s}".format(res))

    def maintenance(self):
        """
        """
        import random
        import time
        from datetime import datetime

        hostid_set = set()
        for k, v in self.host_created.items():
            for i in v:
                hostid_set.add(i)
        if not hostid_set:
            logging.info("Empty hostids to create maintenance.")
            return 
        maintenance_name = datetime.now().strftime("%Y%m%d") + "-{!s}-{!s}".format(__file__.rsplit(".", 1)[0], random.randint(1000,9999))
        maintenance_period = 60*60*3
        data = {
            "jsonrpc": "2.0",
            "method": "maintenance.create",
            "params": {
                "name": maintenance_name,
                "hostids": list(hostid_set),
                "active_since": int(time.time()),
                "active_till": int(time.time()) + maintenance_period,
                "timeperiods": [
                    {
                        "timeperiod_type": 0,
                        "start_date": int(time.time()) - 300,
                        "period": maintenance_period
                    }
                ]
            },
            "id": self.auth_id,
            "auth": self.auth_token,
        }
        res = self._zbx_request(data)
        res = json.loads(res)
        return res["result"]["maintenanceids"]

    def get_templates(self, template_lst):
        """
        """
        data = {
            "jsonrpc": "2.0",
            "method": "template.get",
            "params":
                {
                    "output": ["templateid"],
                    "filter": {
                        "host": template_lst,
                    }
                },
            "auth": self.auth_token,
            "id": self.auth_id
        }
        res = self._zbx_request(data)
        res = json.loads(res)
        return [i["templateid"] for i in res["result"]]

    def get_groups(self, group_lst):
        """
        """
        data = {
            "jsonrpc": "2.0",
            "method": "hostgroup.get",
            "params":
                {
                    "output": ["groupid"],
                    "filter": {
                        "name": group_lst,
                    }
                },
            "auth": self.auth_token,
            "id": self.auth_id
        }
        res = self._zbx_request(data)
        res = json.loads(res)
        return [i["groupid"] for i in res["result"]]

    def get_proxyid(self, proxy):
        """
        """
        data = {
            "jsonrpc": "2.0",
            "method": "proxy.get",
            "params":
                {
                    "output": ["proxyid"],
                    "filter": {
                        "host": proxy,
                    }
                },
            "auth": self.auth_token,
            "id": self.auth_id
        }
        res = self._zbx_request(data)
        res = json.loads(res)
        return [i["proxyid"] for i in res["result"]]


def init_logger(level):
    """初始化日志 Logger，将日志显示至运行终端。

    Args:
        level <str>: 日志级别。
    """
    logging.basicConfig(
        level = getattr(logging, level.upper()),
        format = "%(asctime)s [%(levelname)s] %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S"
    )

def get_db_conn(type="mysql", kwargs):
    type = type.lower()
    if type in ("mysql",):
        conn = pymysql.connect(**kwargs)
        cursor = conn.cursor()
    elif type in ("pgsql", "postgresql"):
        conn = psycopg2.connect(**kwargs)
        conn.autocommit = True
    else:
        raise Exception("not support the db type now")
    return conn

def cookdata_database(db_type, db_conn, filter_set=set()):
    col_mapping = {
        # VC 地址决定 zabbix proxy
        "vm_vcenter_ip": "",
        # 在 IP 缺失或重合的场景，虚拟机名具有重要作用
        "vm_name": "",
        # 虚拟机在客户端识别的操作系统可以帮助确定主机群组和模板
        "vm_guestfullname": "",
        # 首先需要 IP 地址来设定主机名称和可见名后缀
        "vm_netinfo": "",
        # 如果虚拟机备注空缺则尝试使用可定义字段
        "vm_customvalue": "",
        # 首选虚拟机备注作为可见名称的名称
        "vm_annotation": "",
    }
    re_p_ip = re.compile(r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$")
    res = []

    if db_type in ("mysql", ):
        sql_getvm = "select {!s} from (select * from virtualmachine order by create_time desc limit 10000000) t " \
            "where vm_powerstate = 'poweredOn' and create_time > date_format(now(), '%y-%m-%d') group by t.vm_name".format(", ".join([i for i in col_mapping]))
    elif db_type in ("pgsql", "postgresql"):
        sql_getvm = ""
    else:
        raise Exception("not support the db type {!s}".format(db_type))
    logging.debug("sql_getvm: {!s}".format(sql_getvm))
    with db_conn.cursor() as cursor:
        cursor.execute(sql_getvm)
        res_sql_vm = cursor.fetchall()

    logging.info("Before cookdata, get row number of data: {!s}".format(len(res_sql_vm)))
    for row in res_sql_vm:
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
        logging.debug("Start cookdata:")
        logging.debug(row)
        if row["vm_netinfo"]:
            ip_lst = [i.split('|')[1].strip() for i in row["vm_netinfo"].split(",") if "|" in i]
        else:
            ip_lst = []
        # 1. 确定 主机名称
        # 1.1 仅有一个 IP，则设置为 主机名称
        if len(ip_lst) == 1:
            res_meta["host_name"] = ip_lst[0]
        # 1.2 有多个 IP，则选取与虚拟机名近似的 IP 设置为 主机名称
        elif len(ip_lst) > 1:
            for i in ip_lst:
                if i in row["vm_name"]:
                    res_meta["host_name"] = i
                    break
            else:
                logging.error("Failed to get the host_name from the multi ips, the vm {!s} and ips {!s}.".format(
                    row["vm_name"], ip_lst))
                continue
        # 1.3 没有 IP，且虚拟机名符合 IP 规范，则将虚拟机名设置为 主机名称
        else:
            if row["vm_name"].count(".") == 3:
                logging.info("Not found the ip from {!s}, so use the name for ip.".format(row["vm_name"]))
                res_meta["host_name"] = row["vm_name"]
            else:
                logging.error("Not found the ip from {!s}, and the name of vm is not ip format.".format(row["vm_name"]))
                continue
        if res_meta["host_name"] in filter_set:
            logging.debug("The ip {!s} had be filter.".format(res_meta["host_name"]))
            continue
        logging.debug("Catch host_name of res_meta: {!s}".format(res_meta["host_name"]))

        # 2. 确定代理 Proxy
        try:
            res_meta["proxy"] = ZBX_PROXY_MEMBER[ZBX_PROXY_VC_MAPPING[row["vm_vcenter_ip"]]]
        except Exception as e:
            logging.error("Cannot find the specifial zabbix proxy by vc from vm: {!s}".format(e))
            continue
        logging.debug("Catch proxy of res_meta: {!s}".format(res_meta["proxy"]))

        # 3. 设置为创建立即使用
        res_meta["enabled"] = 0
        logging.debug("Catch enabled of res_meta: {!s}".format(res_meta["enabled"]))

        # 4. 通过 主机名称 确定 agent 的接口监听
        if res_meta["host_name"]:
            res_meta["agent_interface_ip"] = res_meta["host_name"]
            # 默认使用 10050 端口
            res_meta["agent_interface_port"] = 10050
        else:
            logging.error("Cannot use the vm_name for agent listen port, the vm is: {!s}.".format(row["vm_name"]))
            continue
        if not re_p_ip.search(res_meta["agent_interface_ip"]):
            logging.error("The agent_interface_ip is not a ip format: {!s}".format(res_meta["agent_interface_ip"]))
            continue
        logging.debug("Catch agent_interface_ip of res_meta: {!s}".format(res_meta["agent_interface_ip"]))
        logging.debug("Catch agent_interface_port of res_meta: {!s}".format(res_meta["agent_interface_port"]))

        # 5. 确定操作系统、模板和主机群组
        vm_sys = None
        if row["vm_guestfullname"] in ZBX_SYSPREFIX_WIN:
            vm_sys = "windows"
        elif row["vm_guestfullname"] in ZBX_SYSPREFIX_LNX:
            vm_sys = "linux"
        else:
            logging.error("Cannot find the OS(vm_guestfullname) on the vm {!s}.".format(row["vm_name"]))
            continue
        res_meta["group_lst"] = ZBX_SYS_GROUP_MAPPING[vm_sys]
        res_meta["template_lst"] = ZBX_TEMPLATE_SYS_MAPPING[vm_sys]
        logging.debug("Catch group_lst of res_meta: {!s}".format(res_meta["group_lst"]))
        logging.debug("Catch template_lst of res_meta: {!s}".format(res_meta["template_lst"]))

        # 6. 设置可见名称
        # 6.1 如果虚拟机备注可用，则将备注作为可见名称
        if row["vm_annotation"].strip():
            prefix = "LNX" if vm_sys == "linux" else "WIN"
            res_meta["visible_name"] = "{!s}_{!s}_{!s}".format(prefix, row["vm_annotation"], res_meta["agent_interface_ip"])
        # 6.1 如果虚拟机备注不可用，则这里选择报错，标准化啦，这里不填坑了
        else:
            logging.error("Not found the vm_annotation on vm {!s}.".format(row["vm_name"]))
            continue
        logging.debug("Catch visible_name of res_meta: {!s}".format(res_meta["visible_name"]))

        res.append(res_meta)
    logging.info("After cookdata, there are {!s} row number data.".format(len(res)))
    return res


def get_zbxfilter(db_conn):
    """
    """
    filter_set = set()
    sql_zbxnow_ip = "select distinct ip from interface;"
    sql_zbxnow_host = "select distinct host from hosts;"
    with db_conn.cursor() as cursor:
        cursor.execute(sql_zbxnow_ip)
        res_zbxnow_ip = cursor.fetchall()
        cursor.execute(sql_zbxnow_host)
        res_zbxnow_host = cursor.fetchall()
    for i in res_zbxnow_ip:
        filter_set.add(i["ip"])
    logging.debug("After interface.ip, the filter length is {!s}".format(len(filter_set)))
    for i in res_zbxnow_host:
        filter_set.add(i["host"])
    logging.debug("After host.ip, the filter length is {!s}".format(len(filter_set)))
    return filter_set


if __name__ == "__main__":
    from config import *
    init_logger("debug")

    zbx_db_conn = get_db_conn(ZBX_DB_TYPE, ZBX_DB_ARGS)
    atexit.register(lambda x: x.close(), conn)
    zbxapi = ZBXApi(ZBX_API_URL, ZBX_AUTH_USER, ZBX_AUTH_PASSWORD)
    filter_set = get_zbxfilter(zbx_db_conn)

    record_db_type = REGIST_DB_TYPE
    record_db_conn = get_db_conn(REGIST_DB_TYPE, REGIST_DB_ARGS)
    atexit.register(lambda x: x.close(), conn)
    raw_data = cookdata_database(record_db_type, record_db_conn, filter_set)
    zbxapi.create_host_some(raw_data)
