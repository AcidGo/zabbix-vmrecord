SET SQL_MODE='ALLOW_INVALID_DATES';

-- database
CREATE DATABASE `zbx_record` DEFAULT CHARACTER SET utf8;

-- table
CREATE TABLE `virtualmachine` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `vm_vcenter_ip` varchar(20) NOT NULL COMMENT '虚拟机所在的 VC 的 IP',
  `vm_name` varchar(100) NOT NULL COMMENT '虚拟机名称',
  `vm_uuid` varchar(80) NOT NULL DEFAULT '' COMMENT '虚拟机 UUID(uuid)',
  `vm_smbios` varchar(80) NOT NULL DEFAULT '' COMMENT '虚拟机 SMBIOS(instanceUuid)',
  `vm_datacenter` varchar(30) NOT NULL COMMENT '虚拟机所在数据中心',
  `vm_cluster` varchar(30) NOT NULL COMMENT '虚拟机所在集群',
  `vm_host` varchar(20) NOT NULL COMMENT '虚拟机所在主机',
  `vm_powerstate` varchar(10) NOT NULL COMMENT '虚拟机通电状况',
  `vm_boottime` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' COMMENT '虚拟机启动的时间',
  `vm_vmtoolstatus` varchar(30) NOT NULL DEFAULT '' COMMENT '虚拟机 vmtool 状态',
  `vm_guestfullname` varchar(50) DEFAULT NULL COMMENT '虚拟机客户端操作系统',
  `vm_datastore_set` varchar(100) NOT NULL DEFAULT '' COMMENT '虚拟机使用的存储器集合',
  `vm_datastore_provision` bigint(20) NOT NULL COMMENT '虚拟机置备的磁盘空间，单位为 bytes',
  `vm_datastore_used` bigint(20) NOT NULL COMMENT '虚拟机使用的磁盘空间，单位为 bytes',
  `vm_cpu_hotadd` varchar(20) NOT NULL COMMENT '虚拟机 CPU 热添加特性',
  `vm_cpu_corenum` int(11) NOT NULL COMMENT '虚拟机 CPU 个数',
  `vm_cpu_corepersocket` int(11) NOT NULL COMMENT '虚拟机 CPU 每槽核数',
  `vm_mem_hotadd` varchar(20) NOT NULL COMMENT '虚拟机内存热添加特性',
  `vm_mem_size` int(11) NOT NULL COMMENT '虚拟机内存大小，单位为 MB',
  `vm_netinfo` varchar(400) NOT NULL DEFAULT '' COMMENT '虚拟机客户端获取的 IP 地址和 MAC',
  `vm_hostname` varchar(100) NOT NULL DEFAULT '' COMMENT '虚拟机 DNS 名称',
  `vm_customvalue` json NOT NULL COMMENT '虚拟机的自定义注释，格式为 {<kid>:<value>,...}',
  `vm_annotation` varchar(200) NOT NULL DEFAULT '' COMMENT '虚拟机备注信息',
  `vm_modifiedtime` datetime NOT NULL DEFAULT '0000-00-00 00:00:00' COMMENT '虚拟机上一次修改的时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=176247 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPRESSED COMMENT='虚拟机表';