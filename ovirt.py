from __future__ import absolute_import
# Import python libs
import copy
import time
import pprint
import logging
import os
import sys
import salt.utils
# Import salt cloud libs
import salt.utils.cloud
import salt.config as config
from salt.exceptions import (
    SaltCloudSystemExit,
    SaltCloudExecutionFailure,
    SaltCloudExecutionTimeout
)
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import ovirtsdk4.xml as params
import yaml
########################################
url = None
ticket = None
csrf = None
verify_ssl = None
########################################

logging.basicConfig(level=logging.DEBUG, filename='example.log')
'''add logging'''


def get_configured_provider():
    '''
    Return the first configured instance.
    '''
    return config.is_provider_configured(
        __opts__,
        __active_provider_name__ or 'ovirt',
        ('user',)
    )


def connection():  # or connect?
    # global url, username, password, ca_file, connection
    global connection
    url_conn = config.get_cloud_config_value(
        'url', get_configured_provider(), __opts__, search_global=False)
    username_conn = config.get_cloud_config_value(
        'username', get_configured_provider(), __opts__, search_global=False)
    password_conn = config.get_cloud_config_value(
        'password', get_configured_provider(), __opts__, search_global=False)
    ca_file_conn = config.get_cloud_config_value(
        'ca_file', get_configured_provider(), __opts__, search_global=False)
    connection = sdk.Connection(
        url=str(url_conn),
        username=username_conn,
        password=password_conn,
        ca_file=str(ca_file_conn),
        debug=True,
        log=logging.getLogger(),
    )
    test_connection()


def test_connection():  # or connect?
    '''
    check connection to ovirt API
    '''
    try:
        connection.test(raise_exception=True)
    except:
        raise SaltCloudSystemExit(
            "Error: Can't accessing ovirt api, please check configuration, connection and retry")


def list_nodes(call=None):
    '''
    print list of VMs
    '''
    ret = {}
    connection()
    vms_service = connection.system_service().vms_service()
    vms = vms_service.list()

    if call != 'function':
        raise SaltCloudSystemExit(
            'The show_instance action must be called with -f or --function.'
        )
    for vm in vms:
        ret[vm.name] = {}
        ret[vm.name]['id'] = str(vm.id)
    connection.close()
    return ret


def get_name_by_id(id):
    '''
    get name of VM depends on its ID
    '''
    connection()
    name_of_VM = ""
    vms_service = connection.system_service().vms_service()
    vms = vms_service.list()
    for vm in vms:
        if vm.id == id:
            name_of_VM = vm.name
    connection.close()
    return str(name_of_VM)

# service functions end


def show_instance(call=None):
    '''
    print list of VMs
    '''
    connection()
    ret = {}
    vms_service = connection.system_service().vms_service()
    vms = vms_service.list()

    if call != 'function':
        raise SaltCloudSystemExit(
            'The show_instance action must be called with -f or --function.'
        )
    for vm in vms:
        print("{: <50} {}".format(vm.name, vm.id))
        ret[vm.name] = vm.id
    connection.close()
    return ret


def start_vm(id_name, call=None):
    '''
    Using ID of VM or name of VM to start
    '''
    connection()
    vms_service = connection.system_service().vms_service()
    if (id_name.count("-") == 4 and len(id_name) == 36):
        vm_service = vms_service.vm_service(id_name)
        name_of_machine = get_name_by_id(id_name)
        vm_service.start()
    else:
        name_of_VM = 'name=' + str(id_name)
        vm = vms_service.list(search=str(name_of_VM))[0]
        vm_service = vms_service.vm_service(vm.id)
        name_of_machine = str(id_name)
        vm_service.start()
    # Wait till the virtual machine is up:
    while True:
        time.sleep(5)
        vm = vm_service.get()
        if vm.status == types.VmStatus.UP:
            break
    # Check according to salt:
    if call != 'action':
        raise SaltCloudSystemExit(
            'The stop action must be called with -a or --action.'
        )
    connection.close()
    return {'Started': '{0} was started.'.format(name_of_machine)}


def stop_vm(id_name, call=None):
    '''
    Using ID of VM or name of VM to stop
    '''
    connection()
    vms_service = connection.system_service().vms_service()
    if (id_name.count("-") == 4 and len(id_name) == 36):
        vm_service = vms_service.vm_service(id_name)
        name_of_machine = get_name_by_id(id_name)
        vm_service.stop()
    else:
        name_of_VM = 'name=' + str(id_name)
        vm = vms_service.list(search=str(name_of_VM))[0]
        vm_service = vms_service.vm_service(vm.id)
        name_of_machine = str(id_name)
        vm_service.stop()

    # Wait till the virtual machine is down:
    while True:
        time.sleep(5)
        vm = vm_service.get()
        if vm.status == types.VmStatus.DOWN:
            break
    # Check according to salt:
    if call != 'action':
        raise SaltCloudSystemExit(
            'The stop action must be called with -a or --action.'
        )
    connection.close()
    return {'Stopped': '{0} was stopped.'.format(name_of_machine)}


def show_summary(call=None):
    '''
    Provide information about oVirt
    '''
    connection()
    # Get API information from the root service:
    ret = {}
    api = connection.system_service().get()
    ret["version"] = api.product_info.version.full_version
    ret["hosts"] = api.summary.hosts.total
    ret["sds"] = api.summary.storage_domains.total
    ret["users"] = api.summary.users.total
    ret["vms"] = api.summary.vms.total
    print("Version: %s \nHosts: %s \nSds: %s \nUsers: %s \nVMS: %s" % (api.product_info.version.full_version,
                                                                       api.summary.hosts.total, api.summary.storage_domains.total, api.summary.users.total, api.summary.vms.total))
    # Close the connection to the server:
    connection.close()

    # Check according to salt:
    if call != 'function':
        raise SaltCloudSystemExit(
            'The show_instance action must be called with -f or --function.'
        )
    connection.close()
    return ret


def info_vm(id_name, call=None):
    '''
    Using ID/name of VM to get info about
    '''
    connection()
    ret = {}
    vms_service = connection.system_service().vms_service()
    if (id_name.count("-") == 4 and len(id_name) == 36):
        name_of_VM = 'id=' + str(id_name)
        vm = vms_service.list(search=str(name_of_VM))[0]
    else:
        name_of_VM = 'name=' + str(id_name)
        vm = vms_service.list(search=str(name_of_VM))[0]
    ret["affinity_labels"] = vm.affinity_labels
    ret["applications"] = vm.applications
    ret["bios"] = vm.bios
    ret["cdroms"] = vm.cdroms
    ret["cluster"] = vm.cluster
    ret["comment"] = vm.comment
    ret["console"] = vm.console
    ret["cpu"] = vm.cpu
    ret["cpu_profile"] = vm.cpu_profile
    ret["cpu_shares"] = vm.cpu_shares
    ret["creation_time"] = vm.creation_time
    ret["custom_compatibility_version"] = vm.custom_compatibility_version
    ret["custom_cpu_model"] = vm.custom_cpu_model
    ret["custom_emulated_machine"] = vm.custom_emulated_machine
    ret["custom_properties"] = vm.custom_properties
    ret["delete_protected"] = vm.delete_protected
    ret["description"] = vm.description
    ret["disk_attachments"] = vm.disk_attachments
    ret["display"] = vm.display
    ret["domain"] = vm.domain
    ret["external_host_provider"] = vm.external_host_provider
    ret["floppies"] = vm.floppies
    ret["fqdn"] = vm.fqdn
    ret["graphics_consoles"] = vm.graphics_consoles
    ret["guest_operating_system"] = vm.guest_operating_system
    ret["guest_time_zone"] = vm.guest_time_zone
    ret["has_illegal_images"] = vm.has_illegal_images
    ret["high_availability"] = vm.high_availability
    ret["host"] = vm.host
    ret["host_devices"] = vm.host_devices
    ret["href"] = vm.href
    ret["id"] = vm.id
    ret["initialization"] = vm.initialization
    ret["instance_type"] = vm.instance_type
    ret["io"] = vm.io
    ret["katello_errata"] = vm.katello_errata
    ret["large_icon"] = vm.large_icon
    ret["lease"] = vm.lease
    ret["memory"] = vm.memory
    ret["memory_policy"] = vm.memory_policy
    ret["migration"] = vm.migration
    ret["migration_downtime"] = vm.migration_downtime
    ret["multi_queues_enabled"] = vm.multi_queues_enabled
    ret["name"] = vm.name
    ret["next_run_configuration_exists"] = vm.next_run_configuration_exists
    ret["nics"] = vm.nics
    ret["numa_nodes"] = vm.numa_nodes
    ret["numa_tune_mode"] = vm.numa_tune_mode
    ret["origin"] = vm.origin
    ret["original_template"] = vm.original_template
    ret["os"] = vm.os
    ret["payloads"] = vm.payloads
    ret["permissions"] = vm.permissions
    ret["placement_policy"] = vm.placement_policy
    ret["quota"] = vm.quota
    ret["reported_devices"] = vm.reported_devices
    ret["rng_device"] = vm.rng_device
    ret["run_once"] = vm.run_once
    ret["serial_number"] = vm.serial_number
    ret["sessions"] = vm.sessions
    ret["small_icon"] = vm.small_icon
    ret["snapshots"] = vm.snapshots
    ret["soundcard_enabled"] = vm.soundcard_enabled
    ret["sso"] = vm.sso
    ret["start_paused"] = vm.start_paused
    ret["start_time"] = vm.start_time
    ret["stateless"] = vm.stateless
    ret["statistics"] = vm.statistics
    ret["status"] = vm.status
    ret["status_detail"] = vm.status_detail
    ret["stop_reason"] = vm.stop_reason
    ret["stop_time"] = vm.stop_time
    ret["storage_domain"] = vm.storage_domain
    ret["storage_error_resume_behaviour"] = vm.storage_error_resume_behaviour
    ret["tags"] = vm.tags
    ret["template"] = vm.template
    ret["time_zone"] = vm.time_zone
    ret["tunnel_migration"] = vm.tunnel_migration
    ret["type"] = vm.type
    ret["usb"] = vm.usb
    ret["use_latest_template_version"] = vm.use_latest_template_version
    ret["virtio_scsi"] = vm.virtio_scsi
    ret["vm_pool"] = vm.vm_pool
    ret["watchdogs"] = vm.watchdogs
    # Check according to salt:
    if call != 'action':
        raise SaltCloudSystemExit(
            'The stop action must be called with -a or --action.'
        )
    connection.close()
    return ret


def remove_vm(id_name, call=None):
    '''
    Using ID/name of VM to remove
    '''
    connection()
    ret = {}
    vms_service = connection.system_service().vms_service()
    if (id_name.count("-") == 4 and len(id_name) == 36):
        name_of_VM = 'id=' + str(id_name)
        name_of_machine = get_name_by_id(id_name)
        vm = vms_service.list(search=str(name_of_VM))[0]
    else:
        name_of_VM = 'name=' + str(id_name)
        name_of_machine = str(id_name)
        vm = vms_service.list(search=str(name_of_VM))[0]
    # select VM to delete
    vm_service = vms_service.vm_service(vm.id)
    vm_service.remove()
    # Check according to salt:
    if call != 'action':
        raise SaltCloudSystemExit(
            'The stop action must be called with -a or --action.'
        )
    connection.close()
    return {'Destroyed': '{0} was destroyed.'.format(name_of_machine)}


def parse_yaml(filename):
    '''
    parsing yaml file to create object with xml
    there are problem with path to file
    '''
    with open(filename, 'r') as myfile:
        raw_data = myfile.read()
    data = yaml.load(raw_data)
    data = data[0]
    return data


def test_parse(kwargs, call=None):
    '''
    testing purposes <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< FOR GOD SAKE PLEASE DONT FORGET TO DELETE SANYA
    '''
    assert "filename" in kwargs, "Cant found filename parameter in function call"

    vm_info = parse_yaml(kwargs["filename"])
    print(vm_info)
    return(vm_info)
    if call != 'function':
        raise SaltCloudSystemExit(
            'The show_instance action must be called with -f or --function.'
        )


def create_vm(kwargs, call=None):
    '''
    Create VM based on YAML file (must include parameter @ filename = "path/to/file" @ )
    - If C(cow) format is used, disk will by created as sparse, so space will be allocated for the volume as needed, also known as I(thin provision).
    - If C(raw) format is used, disk storage will be allocated right away, also known as I(preallocated).
    '''
    assert "filename" in kwargs, "Can't find filename parameter in function call"

    vm_info = parse_yaml(kwargs["filename"])

    req = "name,common,CPU,memory"
    for i in req.split(","):
        assert i in vm_info, 'Cant find parameter "{0}" in YML file'.format(i)
    assert "memory" in vm_info["memory"], 'Cant find memory parameter in YML file'
    assert "cluster" in vm_info["common"], 'Cant find cluster parameter in YML file'

    connection()
    vms_service = connection.system_service().vms_service()
    vms_service.add(
        types.Vm(
            name=vm_info["name"],
            os=types.OperatingSystem(
                type=vm_info["os_type"] if "os_type" in vm_info else "Other",
            ),
            # ''' tyt vot nuxyya ne rabotaet TODO'''
            # # placement_policy=types.VmPlacementPolicy(
            # #     affinity=types.VmAffinity(
            # #         self.param('placement_policy')
            # #     ),
            # #     hosts=[types.Host(name=self.param('host')), ]
            cpu=types.Cpu(
                topology=types.CpuTopology(
                    cores=vm_info["CPU"]["cores"] if "cores" in vm_info["CPU"] else 1,
                    sockets=vm_info["CPU"]["sockets"] if "sockets" in vm_info["CPU"] else 1,
                    threads=vm_info["CPU"]["threads"] if "threads" in vm_info["CPU"] else 1,
                ),
            ),
            memory=1024 * 1024 * 1024 * int(vm_info["memory"]["memory"]),
            memory_policy=types.MemoryPolicy(
                guaranteed=1024 * 1024 * 1024 * vm_info["memory"]["guaranteed"] if "guaranteed" in vm_info["memory"] else 512 * 1024 * 1024 * int(vm_info["memory"]["memory"]),
                ballooning=vm_info["memory"]["ballooning"] if "ballooning" in vm_info["memory"] else True,
                max=1024 * 1024 * 1024 * vm_info["memory"]["maximum"] if "maximum" in vm_info["memory"] else 2048 * 1024 * 1024 * int(vm_info["memory"]["memory"]),
            ),
            cluster=types.Cluster(
                name=vm_info["common"]["cluster"],
            ),
            template=types.Template(
                name=vm_info["common"]["template"] if "template" in vm_info["common"] else "Blank",
            ),
            description=vm_info["common"]["description"] if "description" in vm_info["common"] else "Not provided",
            comment=vm_info["common"]["comment"] if "comment" in vm_info["common"] else "Not provided",
        ),
    )

    if "disks" in vm_info:
        for disk in vm_info["disks"]:
            attach_disk(disk, vm_info["name"])
    if "networks" in vm_info:
        for network in vm_info["disks"]:
            attach_network(network, vm_info["name"])
    # Check according to salt:
    if call != 'function':
        raise SaltCloudSystemExit(
            'The show_instance action must be called with -f or --function.'
        )
    connection.close()
    return {'Created': '{0} was created.'.format(vmname)}


def attach_network(params, vm_name):
    vms_service = connection.system_service().vms_service()
    name_of_VM = 'name=' + str(vm_name)
    vm = vms_service.list(search=str(name_of_VM))[0]

    assert "network" in params,        "Can't find disk name for in YML file"
    assert "name" in params,        "Can't find disk name for in YML file"

    cluster = system_service.clusters_service().cluster_service(vm.cluster.id).get()
    dcs_service = connection.system_service().data_centers_service()
    dc = dcs_service.list(search='Clusters.name=%s' % cluster.name)[0]
    networks_service = dcs_service.service(dc.id).networks_service()
    network = next(
        (n for n in networks_service.list()
            if n.name == params["network"]),
        None
        )
    profiles_service = connection.system_service().vnic_profiles_service()
    profile_id = None
    for profile in profiles_service.list():
        if profile.name == params["network"]:
            profile_id = profile.id
            break

    nics_service = vms_service.vm_service(vm.id).nics_service()

    # Use the "add" method of the network interface cards service to add the
    # new network interface card:
    nics_service.add(
        types.Nic(
            name=params["name"],
            description=params["description"] if "description" in params else "Not provided",
            vnic_profile=types.VnicProfile(id=profile_id,
            ),
        ),
    )

    # Check according to salt:

def attach_disk(params, vm_name):

    vms_service = connection.system_service().vms_service()
    name_of_VM = 'name=' + str(vm_name)
    vm = vms_service.list(search=str(name_of_VM))[0]
    disk_attachments_service = vms_service.vm_service(vm.id).disk_attachments_service()

    assert "name" in params,        "Can't find disk name for in YML file"
    assert "format" in params,      "Can't find disk format in YML file"
    assert "interface" in params,   "Can't find disk interface in YML file"
    assert "active" in params,      "Can't find disk active in YML file"
    assert "bootable" in params,    "Can't find disk bootable parameter in YML file"

    if params["format"].lower() == "raw":
        disk_format = types.DiskFormat.RAW
    elif params["format"].lower() == "cow":
        disk_format = types.DiskFormat.COW
    else:
        return("Cant determinate format of disk. Supported only RAW and COW")
        raise SaltCloudExecutionFailure

    if params["interface"].lower() == "virtio":
        disk_interface = types.DiskInterface.VIRTIO
    else:
        return("Cant determinate format of disk. Supported only RAW and COW")
        raise SaltCloudExecutionFailure

    disk_attachment = disk_attachments_service.add(
        types.DiskAttachment(
            disk=types.Disk(
                name=params["name"],
                description=params["description"] if "description" in params else "Not provided",
                format=disk_format,
                provisioned_size=int(params["provisioned_size"]) * 2**30,
                storage_domains=[
                    types.StorageDomain(
                        name=params["storage_domains"],
                    ),
                ],
            ),
            interface=disk_interface,
            bootable=params["bootable"],
            active=params["active"],
        ),
    )
