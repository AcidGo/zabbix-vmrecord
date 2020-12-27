# Author: AcidGo

import atexit
import datetime
import logging
import json
import sys
import time

from config import *
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
from sqlalchemy import create_engine
from sqlalchemy import BigInteger, Column, DateTime, Integer, JSON, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class VMReport(Base):
    __tablename__ = "vmreport"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    create_time = Column(DateTime, nullable=False, comment="创建批次时间")
    vm_vcenter_ip = Column(String(20), nullable=False, comment="虚拟机所在的 VC 的 IP")
    vm_name = Column(String(100), nullable=False, comment="虚拟机名称")
    vm_uuid = Column(String(80), nullable=False, default="", comment="虚拟机 UUID(uuid)'")
    vm_smbios = Column(String(80), nullable=False, default="", comment="虚拟机 SMBIOS(instanceUuid)")
    vm_datacenter = Column(String(30), nullable=False, comment="虚拟机所在数据中心")
    vm_cluster = Column(String(30), nullable=False, comment="虚拟机所在集群")
    vm_host = Column(String(20), nullable=False, comment="虚拟机所在主机")
    vm_powerstate = Column(String(10), nullable=False, comment="虚拟机通电状况")
    vm_boottime = Column(DateTime, comment="虚拟机启动的时间")
    vm_vmtoolstatus = Column(String(30), nullable=False, default="", comment="虚拟机 vmtool 状态")
    vm_guestfullname = Column(String(50), comment="虚拟机客户端操作系统")
    vm_datastore_set = Column(String(100), nullable=False, comment="虚拟机使用的存储器集合")
    vm_datastore_provision = Column(BigInteger, nullable=False, comment="虚拟机置备的磁盘空间，单位为 bytes")
    vm_datastore_used = Column(BigInteger, nullable=False, comment="虚拟机使用的磁盘空间，单位为 bytes")
    vm_cpu_hotadd = Column(String(20), nullable=False, comment="虚拟机 CPU 热添加特性")
    vm_cpu_corenum = Column(Integer, nullable=False, comment="虚拟机 CPU 个数")
    vm_cpu_corepersocket = Column(Integer, nullable=False, comment="虚拟机 CPU 每槽核数")
    vm_mem_hotadd = Column(String(20), nullable=False, comment="虚拟机内存热添加特性")
    vm_mem_size = Column(Integer, nullable=False, comment="虚拟机内存大小，单位为 MB")
    vm_netinfo = Column(JSON, comment="虚拟机客户端获取的 IP 地址和 MAC")
    vm_hostname = Column(String(100), nullable=False, default="", comment="虚拟机 DNS 名称")
    vm_customvalue = Column(JSON, comment="虚拟机的自定义注释，格式为 {<kid>:<value>,...}")
    vm_annotation = Column(String(200), nullable=False, default="", comment="虚拟机备注信息")
    vm_modifiedtime = Column(DateTime, comment="虚拟机上一次修改的时间")

class VMWorker(object):
    """执行 vSphere 虚拟机相关工作。
    """
    use_ssl = False
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

    def __init__(self):
        self._vc_reset()

    def _vc_reset(self):
        self._args = {}
        self._data = None
        self._atexit_func = None

    def vc_login(self, **kwargs):
        """登录 vCenter 的用户认证，可以直接对接 ESXi，但不建议。

        Args:
            kwargs: 登录认证信息。
        """
        self._vc_reset()
        connect = SmartConnect if self.use_ssl is True else SmartConnectNoSSL
        try:
            service_instance = connect(**kwargs)
        except vim.fault.InvalidLogin as e:
            raise Exception(e.msg)
        self.service_instance = service_instance
        # 注册程序退出后的 VC 连接断开
        self._atexit_func = atexit.register(Disconnect, self.service_instance)
        self._args.update({k: v for k, v in kwargs.items() if k.lower() != "pwd"})

    def vc_logout(self):
        """
        """
        if self.service_instance is None:
            Disconnect(self.service_instance)
        if self._atexit_func is not None:
            atexit.unregister(self._atexit_func)
            self._atexit_func = None

    def set_data(self, data):
        self._data = data

    def get_data(self):
        return self._data

    def collect(self):
        """收集虚拟机的信息。
        """
        if not self.service_instance:
            raise Exception("unable to connect to host with supplied info")

        view = self._get_container_view(obj_type=[vim.VirtualMachine])
        vm_data = self._collect_properties(
            view_ref = view,
            obj_type = vim.VirtualMachine,
            path_set = self.vm_properties,
            include_mors = False,
        )
        for i in vm_data:
            i.update({"vc.ip": self._args.get("host", "")})
        self._data = vm_data

    def _get_container_view(self, obj_type, container=None):
        """从指定层次获取指定对象的搜寻视图。
        """
        if not container:
            container = self.service_instance.content.rootFolder

        view_ref = self.service_instance.content.viewManager.CreateContainerView(
            container=container,
            type=obj_type,
            recursive=True
        )
        return view_ref

    def _collect_properties(self, view_ref, obj_type, path_set=None, include_mors=False):
        """通过传入的视图遍历指定对象的相关属性。
        """
        collector = self.service_instance.content.propertyCollector

        obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.obj = view_ref
        obj_spec.skip = True

        traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.name = 'traverseEntities'
        traversal_spec.path = 'view'
        traversal_spec.skip = False
        traversal_spec.type = view_ref.__class__
        obj_spec.selectSet = [traversal_spec]

        property_spec = vmodl.query.PropertyCollector.PropertySpec()
        property_spec.type = obj_type

        if not path_set:
            property_spec.all = True
        property_spec.pathSet = path_set

        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = [obj_spec]
        filter_spec.propSet = [property_spec]

        props = collector.RetrieveContents([filter_spec])

        data = []
        _host_parent_mapping = {}
        for obj in props:
            properties = {}
            for prop in obj.propSet:
                if prop.name == "customValue":
                    tmp_dict = {}
                    for tmp_i in prop.val:
                        tmp_dict[tmp_i.key] = tmp_i.value
                    res = tmp_dict
                elif prop.name == "guest.net":
                    tmp_list = []
                    for tmp_i in prop.val:
                        mac_ = tmp_i.macAddress
                        ip_ = None
                        if isinstance(tmp_i.ipAddress, list):
                            for j in tmp_i.ipAddress:
                                if j.count(".") >= 3:
                                    ip_ = j
                        tmp_list.append((mac_, ip_))
                    res = tmp_list
                elif prop.name == "datastore":
                    tmp_set = set()
                    for tmp_i in prop.val:
                        tmp_set.add(tmp_i.name)
                    res = tmp_set
                elif prop.name == "runtime.host":
                    res = prop.val.name
                    if res not in _host_parent_mapping:
                        host_cluster = prop.val.parent.name
                        cluster_datacenter = prop.val.parent.parent.parent.name
                        _host_parent_mapping[res] = (cluster_datacenter, host_cluster)
                    properties["host.datacenter"] = _host_parent_mapping[res][0]
                    properties["host.cluster"] = _host_parent_mapping[res][1]
                elif prop.name == "storage.perDatastoreUsage":
                    committed = 0
                    uncommitted = 0
                    unshared = 0
                    for tmp_i in prop.val:
                        committed += tmp_i.committed
                        uncommitted += tmp_i.uncommitted
                        unshared += tmp_i.unshared
                    properties["storage.perDatastoreUsage.provision"] = committed + uncommitted
                    properties["storage.perDatastoreUsage.committed"] = committed
                    continue
                else:
                    res = prop.val
                properties[prop.name] = res
            if include_mors:
                properties['obj'] = obj.obj
            data.append(properties)

        return data

class Reporter(VMWorker):
    def report(self):
        raise Exception("please overwrite me")

class DBReporter(Reporter):
    def __init__(self):
        super(DBReporter, self).__init__()
        self._db_session = None
        self._create_time = datetime.datetime.now()

    def report(self):
        if self._db_session is None:
            raise Exception("not found mysql conn for reporting data")
        logging.info("starting for report the data to database ......")
        for line in self.get_data():
            logging.debug("starting deal with getten data: {!s}".format(line))
            row = VMReport(
                create_time = self._create_time,
                vm_vcenter_ip = line["vc.ip"],
                vm_name = line["name"],
                vm_uuid = line["config.uuid"],
                vm_smbios = line["config.instanceUuid"],
                vm_datacenter = line["host.datacenter"],
                vm_cluster = line["host.cluster"],
                vm_host = line["runtime.host"],
                vm_powerstate = line["runtime.powerState"],
                vm_boottime = line["runtime.bootTime"] if "runtime.bootTime" in line else None,
                vm_vmtoolstatus = line.get("guest.toolsStatus", ""),
                vm_guestfullname = line["config.guestFullName"],
                vm_datastore_set = "|".join(line["datastore"]),
                vm_datastore_provision = line["storage.perDatastoreUsage.provision"],
                vm_datastore_used = line["storage.perDatastoreUsage.committed"],
                vm_cpu_hotadd = line["config.cpuHotAddEnabled"],
                vm_cpu_corenum = line["config.hardware.numCPU"],
                vm_cpu_corepersocket = line["config.hardware.numCoresPerSocket"],
                vm_mem_hotadd = line["config.memoryHotAddEnabled"],
                vm_mem_size = line["config.hardware.memoryMB"],
                vm_netinfo = {i[0]: i[1] for i in line["guest.net"]},
                vm_hostname = line.get("guest.hostName", ""),
                vm_customvalue = {k: v for k, v in line["customValue"].items()},
                vm_annotation = line.get("config.annotation", ""),
                vm_modifiedtime = line["config.modified"],
            )
            try:
                self._db_session.add(row)
                self._db_session.commit()
            except Exception as e:
                logging.error("get an err when add row for data: {!s}".format(e))
                logging.exception(e)
            else:
                logging.debug("finished for report the row to database: {!s}".format(line["name"]))
        logging.info("finished for report the data to database")

    def db_login(self, db_urls):
        """
        """
        # NOTICE: debug mode
        # engine = create_engine(db_urls, echo=True)
        # EOF NOTICE
        engine = create_engine(
            db_urls, 
            json_serializer = lambda obj: json.dumps(obj, ensure_ascii=False),
            connect_args = {"connect_timeout": 10},
        )
        Base.metadata.create_all(engine)
        self._db_session = sessionmaker(engine)()
        logging.info("initializing database session is finished")

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
    # ########## Self Test
    # mock_data = [
    #     {
    #         "vc.ip": "196.1.1.101",
    #         "name": "192.168.66.31",
    #         "config.uuid": "abcd",
    #         "config.instanceUuid": "abcd",
    #         "host.datacenter": "abcd",
    #         "host.cluster": "abcd",
    #         "runtime.host": "abcd",
    #         "runtime.powerState": "poweredOn",
    #         "runtime.bootTime": None,
    #         "guest.toolsStatus": "",
    #         "config.guestFullName": "Red Hat Enterprise Linux 6 (64 位)",
    #         "datastore": "",
    #         "storage.perDatastoreUsage.provision": 100,
    #         "storage.perDatastoreUsage.committed": 200,
    #         "config.cpuHotAddEnabled": "",
    #         "config.hardware.numCPU": 2,
    #         "config.hardware.numCoresPerSocket": 3,
    #         "config.memoryHotAddEnabled": "",
    #         "config.hardware.memoryMB": 100,
    #         "guest.net": "",
    #         "guest.hostName": "",
    #         "customValue": {},
    #         "config.annotation": "XYZEVA",
    #         "config.modified": None,
    #     }
    # ]
    # ########## EOF Self Tes

    init_logger("info")
    try:
        reporter = DBReporter()
        reporter.db_login(REPORT_DB_URLS)
        for vc, vc_login_args in VCCONFIG.items():
            logging.info("starting deal with reporting for vc {!s}".format(vc))
            try:
                reporter.vc_login(**vc_login_args)
                reporter.collect()
                # NOTICE: only testing
                # reporter.set_data(mock_data)
                # EOF NOTICE
                reporter.report()
            except Exception as e:
                logging.error("get an err when deal with reporting for vc {!s}: {!s}".format(vc, e))
                logging.exception(e)
            logging.info("finished deal with reporting for vc {!s}".format(vc))
    except Exception as e:
        logging.exception(e)
        exit(1)