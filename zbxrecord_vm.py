# -*- coding: utf-8 -*-
# Author: AcidGo
# Usage: 展示 VMware 的定制信息，进行报表展示。



import atexit
import time, sys
import logging
from config import *
import pymysql
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect


def collect_properties(service_instance, view_ref, obj_type, path_set=None,
                       include_mors=False):
    collector = service_instance.content.propertyCollector

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



def get_container_view(service_instance, obj_type, container=None):
    if not container:
        container = service_instance.content.rootFolder

    view_ref = service_instance.content.viewManager.CreateContainerView(
        container=container,
        type=obj_type,
        recursive=True
    )
    return view_ref
    
    
def network_info(nt_obj):
    res = " "
    if isinstance(nt_obj, str):
        return res
    else:
        try:
            tmp_lst = []
            for i in nt_obj:
                if isinstance(i.ipAddress, list):
                    for j in i.ipAddress:
                        if j.count(".") >= 3:
                            tmp_lst.append(j)
                else:
                    tmp_lst.append(i.ipAddress)
            if len(tmp_lst) == 0:
                return " "
            res = " | ".join(tmp_lst)
        except Exception as e:
            res = " "
        return res


def data_execute(conn_cursor, data):
    """
    """
    import pymysql

    print(data["name"])
    vm_vcenter_ip = data["vc.ip"]
    vm_name = data["name"]
    vm_uuid = data["config.uuid"]
    vm_smbios = data["config.instanceUuid"]
    vm_datacenter = data["host.datacenter"]
    vm_cluster = data["host.cluster"]
    vm_host = data["runtime.host"]
    vm_powerstate = data["runtime.powerState"]
    vm_boottime = data["runtime.bootTime"].strftime("%Y-%m-%d %H:%M:%S") if "runtime.bootTime" in data else None
    vm_vmtoolstatus = data.get("guest.toolsStatus", "")
    vm_guestfullname = data["config.guestFullName"]
    vm_datastore_set = "|".join(data["datastore"])
    vm_datastore_provision = data["storage.perDatastoreUsage.provision"]
    vm_datastore_used = data["storage.perDatastoreUsage.committed"]
    vm_cpu_hotadd = data["config.cpuHotAddEnabled"]
    vm_cpu_corenum = data["config.hardware.numCPU"]
    vm_cpu_corepersocket = data["config.hardware.numCoresPerSocket"]
    vm_mem_hotadd = data["config.memoryHotAddEnabled"]
    vm_mem_size = data["config.hardware.memoryMB"]
    vm_netinfo = ",".join(["{!s}|{!s}".format(i[0], i[1]) for i in data["guest.net"]]) 
    vm_hostname = data.get("guest.hostName", "")
    vm_customvalue = ",".join(["{!s}:[{!s}]".format(k, v) for k, v in data["customValue"].items()])
    vm_annotation = data.get("config.annotation", "")
    vm_modifiedtime = data["config.modified"].strftime("%Y-%m-%d %H:%M:%S")

    data_dict = {k: v for k, v in locals().items() if k.startswith("vm_")}

    sql = "INSERT INTO `virtualmachine` (vm_vcenter_ip , vm_name , vm_uuid , vm_smbios , vm_datacenter , vm_cluster , " \
        "vm_host , vm_powerstate , vm_boottime , vm_vmtoolstatus , vm_guestfullname , vm_datastore_set , vm_datastore_provision , " \
        "vm_datastore_used , vm_cpu_hotadd , vm_cpu_corenum , vm_cpu_corepersocket , vm_mem_hotadd , vm_mem_size , vm_netinfo , " \
        "vm_hostname , vm_customvalue , vm_annotation , vm_modifiedtime) " \
        "VALUES(%(vm_vcenter_ip)s, %(vm_name)s, %(vm_uuid)s, %(vm_smbios)s, %(vm_datacenter)s, %(vm_cluster)s, %(vm_host)s, " \
        "%(vm_powerstate)s, %(vm_boottime)s, %(vm_vmtoolstatus)s, %(vm_guestfullname)s, %(vm_datastore_set)s, %(vm_datastore_provision)s, " \
        "%(vm_datastore_used)s, %(vm_cpu_hotadd)s, %(vm_cpu_corenum)s, %(vm_cpu_corepersocket)s, %(vm_mem_hotadd)s, %(vm_mem_size)s, " \
        "%(vm_netinfo)s, %(vm_hostname)s, %(vm_customvalue)s, %(vm_annotation)s, %(vm_modifiedtime)s)"
    try:
        effect_row = cursor.execute(sql, data_dict)
    except Exception as e:
        print("Get error when execute sql: {!s}".format(e))
    else:
        print("effect_row: {!s}".format(effect_row))


if __name__ == "__main__":
    # 列举的vm属性的列表
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

    conn = pymysql.connect(
        host = DB_HOST,
        port = DB_PORT,
        user = DB_USER,
        password = DB_PASSWORD,
        db = DB_SCHEMA,
        charset = DB_CHARSET,
        cursorclass = pymysql.cursors.DictCursor,
        autocommit = True
    )
    cursor = conn.cursor()

    for vc_name, vc_config in VCCONFIG.items():
        HOST = vc_config["vchost"]
        USER = vc_config["vcuser"]
        PASSWORD = vc_config["vcpassword"]

        service_instance = None
        try:
            service_instance = SmartConnectNoSSL(host=HOST,
                                                    user=USER,
                                                    pwd=PASSWORD,
                                                    port=443)
            atexit.register(Disconnect, service_instance)
            search_index = service_instance.content.searchIndex
        except IOError as e:
            pass

        if not service_instance:
            raise SystemExit("Unable to connect to host with supplied info.")

        root_folder = service_instance.content.rootFolder

        view = get_container_view(service_instance,
                                           obj_type=[vim.VirtualMachine])
        vm_data = collect_properties(
            service_instance, 
            view_ref=view,
            obj_type=vim.VirtualMachine,
            path_set=vm_properties,
            include_mors=False
        )
        for i in vm_data:
            i.update({"vc.ip": HOST})
            data_execute(cursor, i)