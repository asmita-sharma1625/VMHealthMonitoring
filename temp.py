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


def fetch_disk_stats(dom):
    tree = ElementTree.fromstring(dom.XMLDesc())
    disk = tree.find('devices/disk/target').get('dev')
    stats = dom.blockStats(disk)
    return stats


def get_disk_errors(dom):
    return dom.diskErrors()


def get_instance_state(dom):
    return dom.isActive()


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
    i=1
    while i==1:
        i =2
        message = []

        vms = conn.listAllDomains()
        for vm in vms:
            try:
                dom = vm
                name = dom.name()
                print name
                dom_uuid = dom.UUIDString()
            except libvirt.libvirtError, err:
                continue
            if name == "Domain-0":
                continue
            state = get_instance_state(dom)
            account_id = get_account_id(dom)
            try:
                instance_name = get_instance_name(dom)
            except Exception:
                instance_name = str(dom_uuid)
            prev_vm_dict[id] = dict()
            prev_vm_dict[id]['state'] = state
            prev_vm_dict[id]['account_id'] = account_id
            message.append('VmState,InstanceId=' + instance_name +
                  ',Namespace=JCS/Compute,Unit=Count,AccountId='+ account_id +
                  ' value=' + str(state) + ' ' + str(state) + '\n')
            #print('write packets: '+str(netstats[5]))
            #print('write errors:  '+str(netstats[6]))
            #print('write drops:   '+str(netstats[7]))
        print message
'''
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
'''

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

