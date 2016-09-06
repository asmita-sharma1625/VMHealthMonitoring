#!/usr/bin/python
# vim: set fileencoding=utf-8 :
#
#
#%# capabilities=autoconf
#%# family=contrib

import re, sys, os
import libvirt
import time
from datetime import datetime
from xml.etree import ElementTree
import uuid
import socket
import MySQLdb

CPU_TIME_INTERVAL = 60
HOSTNAME = socket.gethostname()


def fetch_cputime(dom):
    num_cpu = float(dom.info()[3])
    cputime = float(dom.info()[4])
    cputime_ms = 1.0e-6 * cputime / num_cpu
    #print "%s_cputime.value %.0f" % (canon(name), cputime_percentage)
    return cputime_ms


def get_instance_name(dom):
    ns = {'nova': 'http://openstack.org/xmlns/libvirt/nova/1.0'}
    tree = ElementTree.fromstring(dom.XMLDesc())
    name = tree.find('metadata/nova:instance/nova:name', ns).text
    return name


def get_account_id(dom):
    ns = {'nova': 'http://openstack.org/xmlns/libvirt/nova/1.0'}
    tree = ElementTree.fromstring(dom.XMLDesc())
    acc_id = tree.find('metadata/nova:instance/nova:owner/nova:project', ns).get('uuid')
    return acc_id
    

def fetch_network_stats(dom):
    tree = ElementTree.fromstring(dom.XMLDesc())
    iface = tree.find('devices/interface/target').get('dev')
    stats = dom.interfaceStats(iface)
    return stats


def fetch_disk_stats(dom):
    tree = ElementTree.fromstring(dom.XMLDesc())
    disk = tree.find('devices/disk/target').get('dev')
    stats = dom.blockStats(disk)
    return stats


def fetch_memory_stats(dom):
    memstats = dom.memoryStats()
    return memstats

def get_account_id_from_db(uuid):
    db = MySQLdb.connect(host="csdb1-staging",
                     user="nova",
                     passwd="eA97AEbB",
                     db="nova")
    cur = db.cursor()
    cur.execute("select project_id from instances where uuid = \"" + uuid +"\";")
    row = cur.fetchone()
    if row is not None:
        return str(row[0])
    else:
        return "0"

def periodic_metrics_calc(conn):
    # the previous iteration data will be stored in below dict
    # prev_vm_dict = {'<vm_id>':{
    #   'utc_time' : <utc_time>,
    #   'cpu_time' : <cpu_cycles>,
    #   'tx_bytes' : <tx_bytes>,
    #   'tx_packets': <tx_packets>,
    #   'rx_bytes' : <rx_bytes>,
    #   'rx_packets': <rx_packets>
    # }}
    TCP_IP = '127.0.0.1'
    TCP_PORT = 8094

    prev_vm_dict = dict()
    while True:
        message = []

        ids = conn.listDomainsID()
        for id in ids:
            try:
                dom = conn.lookupByID(id)
                name = dom.name()
                dom_uuid = uuid.UUID(bytes=dom.UUID())
            except libvirt.libvirtError, err:
                continue
            if name == "Domain-0":
                continue
            cputime = fetch_cputime(dom)
            curr_utc_time = time.time()
            percent_cpu = 0
            rx_bytes = 0
            rx_packets = 0
            tx_bytes = 0
            tx_packets = 0
            rd_request = 0
            wr_request = 0
            rd_bytes = 0
            wr_bytes = 0
            netstats = fetch_network_stats(dom)
            diskstats = fetch_disk_stats(dom)
            try:
                instance_name = get_instance_name(dom)
            except Exception:
                instance_name = str(dom_uuid)
            try:
                time_lapsed = (curr_utc_time - prev_vm_dict[id]['utc_time'])
                percent_cpu = (cputime - prev_vm_dict[id]['cpu_time']) /\
                    time_lapsed / 10 #percent cpu in ms time_lapsed in s
                rx_bytes = (netstats[0] - prev_vm_dict[id]['rx_bytes'])
                rx_packets = (netstats[1] - prev_vm_dict[id]['rx_packets'])
                tx_bytes = (netstats[4] - prev_vm_dict[id]['tx_bytes'])
                tx_packets = (netstats[5] - prev_vm_dict[id]['tx_packets'])
                rd_request = (diskstats[0] - prev_vm_dict[id]['rd_req'])
                rd_bytes = (diskstats[1] - prev_vm_dict[id]['rd_bytes'])
                wr_request = (diskstats[2] - prev_vm_dict[id]['wr_req'])
                wr_bytes = (diskstats[3] - prev_vm_dict[id]['wr_bytes'])
                account_id = prev_vm_dict[id]['account_id']
            except Exception:
                try:
                    account_id = get_account_id(dom)
                except Exception:
                    account_id = get_account_id_from_db(str(dom_uuid))
            prev_vm_dict[id] = dict()
            prev_vm_dict[id]['cpu_time'] = cputime
            prev_vm_dict[id]['utc_time'] = curr_utc_time
            # memstats = fetch_memory_stats(dom)
            # for memname in memstats:
            #     print('  '+str(memstats[memname])+' ('+memname+')')
            prev_vm_dict[id]['rx_bytes'] = netstats[0]
            prev_vm_dict[id]['rx_packets'] = netstats[1]
            prev_vm_dict[id]['tx_bytes'] = netstats[4]
            prev_vm_dict[id]['tx_packets'] = netstats[5]
            prev_vm_dict[id]['rd_req'] = diskstats[0]
            prev_vm_dict[id]['rd_bytes'] = diskstats[1]
            prev_vm_dict[id]['wr_req'] = diskstats[2]
            prev_vm_dict[id]['wr_bytes'] = diskstats[3]
            prev_vm_dict[id]['account_id'] = account_id
            rounded_time = curr_utc_time - (curr_utc_time % 60)
            curr_utc_time_str = '{:.0f}'.format(rounded_time * 1.0e09)
            message.append('CPUUtilization,InstanceId=' + instance_name + 
                  ',Namespace=JCS/Compute,Unit=Percent,AccountId='+ account_id +
                  ' value=' + str(percent_cpu) + ' ' + str(curr_utc_time_str) + '\n')
            message.append('NetworkBytesIn,InstanceId=' + instance_name +
                  ',Namespace=JCS/Compute,Unit=Bytes,AccountId='+ account_id +
                  ' value=' + str(rx_bytes) + ' ' + str(curr_utc_time_str) + '\n')
            message.append('NetworkPacketsIn,InstanceId=' + instance_name +
                  ',Namespace=JCS/Compute,Unit=Count,AccountId='+ account_id +
                  ' value=' + str(rx_packets) + ' ' + str(curr_utc_time_str) + '\n')
            #print('read errors:   '+str(netstats[2]))
            #print('read drops:    '+str(netstats[3]))
            #print('write bytes:   '+str(netstats[4]))
            message.append('NetworkBytesOut,InstanceId=' + instance_name +
                  ',Namespace=JCS/Compute,Unit=Bytes,AccountId='+ account_id +
                  ' value=' + str(tx_bytes) + ' ' + str(curr_utc_time_str) + '\n')
            message.append('NetworkPacketsOut,InstanceId=' + instance_name +
                  ',Namespace=JCS/Compute,Unit=Count,AccountId='+ account_id +
                  ' value=' + str(tx_packets) + ' ' + str(curr_utc_time_str) + '\n')
            message.append('DiskReadBytes,InstanceId=' + instance_name +
                  ',Namespace=JCS/Compute,Unit=Bytes,AccountId='+ account_id +
                  ' value=' + str(rd_bytes) + ' ' + str(curr_utc_time_str) + '\n')
            message.append('DiskReadOps,InstanceId=' + instance_name +
                  ',Namespace=JCS/Compute,Unit=Count,AccountId='+ account_id +
                  ' value=' + str(rd_request) + ' ' + str(curr_utc_time_str) + '\n')
            message.append('DiskWriteBytes,InstanceId=' + instance_name +
                  ',Namespace=JCS/Compute,Unit=Bytes,AccountId='+ account_id +
                  ' value=' + str(wr_bytes) + ' ' + str(curr_utc_time_str) + '\n')
        message.append('DiskWriteOps,InstanceId=' + instance_name +
                  ',Namespace=JCS/Compute,Unit=Count,AccountId='+ account_id +
                  ' value=' + str(wr_request) + ' ' + str(curr_utc_time_str) + '\n')
            #print('write packets: '+str(netstats[5]))
            #print('write errors:  '+str(netstats[6]))
            #print('write drops:   '+str(netstats[7]))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((TCP_IP, TCP_PORT))
        for msg in message:
            #print msg
            s.sendall(msg)
        s.close()
        curr_id_set = set(ids)
        deleted_id_list = [x for x in prev_vm_dict.keys() if x not in
                           curr_id_set]
        for i in deleted_id_list:
            del prev_vm_dict[i]
        curr_utc_time = datetime.utcnow()
        make_prog_sleep = 60 - (curr_utc_time.second + curr_utc_time.microsecond/1000000.0)
        #make_prog_sleep = (2 * CPU_TIME_INTERVAL) - time_lapsed
        time.sleep(make_prog_sleep)


def fetch_values(uri):
    conn = libvirt.openReadOnly(uri)
    periodic_metrics_calc(conn)
    #for id in ids:
    #    try:
    #        dom = conn.lookupByID(id)
    #        name = dom.name()
    #    except libvirt.libvirtError, err:
    #        print >>sys.stderr, "Id: %s: %s" % (id, err)
    #        continue
    #    if name == "Domain-0":
    #        continue
    #    cpu_time = fetch_cputime(dom)
    #    cpu_stats = dom.getCPUStats(False)
    #    for (i, cpu) in enumerate(cpu_stats):
    #        print('CPU '+str(i)+' Time: '+str(cpu['cpu_time'] / 1000000000.))

    #    stats = dom.getCPUStats(True)
    #    print('cpu_time:    '+str(stats[0]['cpu_time']))
    #    print('system_time: '+str(stats[0]['system_time']))
    #    print('user_time:   '+str(stats[0]['user_time']))


def main(sys):
    uri = os.getenv("uri", "qemu:///system")
    if len(sys) > 1:
        if sys[1] in ['autoconf', 'detect']:
            if libvirt.openReadOnly(uri):
                print "yes"
                return 0
            else:
                print "no"
                return 1
    fetch_values(uri)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))

