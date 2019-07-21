#!/usr/bin/python
from fio_configurations import fio_configurations
import os
import re
import subprocess
# Helper function for scanning /sys/block/ for devices.
def walk(path):
    for (path, block_devices, irrelevant) in os.walk(path,topdown=True):
        devices = [device for device in block_devices if not_filtered(device)]
        return devices
# Helper function for handling the os module from Python.
def parser(command, parent_directory, device_name, additional_arguments):
    device_name = str(device_name)
    parsed = os.popen(command + " " + 
                parent_directory + device_name + additional_arguments).readlines()
    return next(iter(parsed),None).split('\n')[0]
# Filter out loop devices from /sys/block/ output.
def not_filtered(device):
    #Loopback devices like in-memory snap devices.
    if 'loop' in device:
        return False
    #Serial read devices like CD-ROM drives.
    if 'sr' in device:
        return False
    # If all filters passed, then this is not a filtered device.
    return True
# Builds a Dictionary object for each device to pass into fio_configurations.
def device_attributes(device):
    attributes = {
        'name'       : '/dev/' + device,
        'model'      : model(device),
        'size'       : capacity(device),
        'serial'     : serial_number(device),
        'firmware'   : firmware(device),
        'type'       : device_type(device),
        'interface'  : device_interface(device),
        'queue_depth': queue_depth(device),
        'block_size' : block_size(device)
    }
    return attributes
# Captures the human-readable model name of the drive.
def model(device):
    return str(parser("cat", "/sys/block/", device, "/device/model"))
# Captures the size of available space; returns size in GB.
def capacity(device):
    amount_in_bytes = int(parser("cat", "/sys/block/", device, "/size")) * 512
    amount_in_gigabytes = amount_in_bytes / (1024 * 1024 * 1024)
    return str(amount_in_gigabytes) + " GB"
# WWID includes: device type (e.g. t10.ATA), Model name, Serial Number.
def device_interface(device):
    wwid = "".join(parser("cat", "/sys/block/", device, "/device/wwid"))
    regex = re.findall(r'\S+', wwid)
    transport = regex[0]
    if 't10' in transport:
        transport = 'S' + transport.split('.')[1]
    # If the device type is t10, then it does not have a WWN.
    return transport
# We can capture the serial number from the WWID.
def serial_number(device):
    # WWID includes: device type (e.g. t10.ATA), Model name, Serial Number.
    # If the device type is t10, then it does not have a WWN.
    wwid = "".join(parser("cat", "/sys/block/", device, "/device/wwid"))
    regex = re.findall(r'\S+', wwid)
    serial = regex[-1]
    return serial
# Captures the last four digits of the device's firmware revision.
def firmware(device):
    return str(parser("cat", "/sys/block/", device, "/device/rev"))
# Check whether the drive is an HDD, SSD, or NVMe drive.
def device_type(device):
    # If the device reports a rotation of 0, it is an SSD.
    parsed = parser("cat", "/sys/block/", device, "/queue/rotational")
    if int(parsed) == 0:
        # All NVMe drives include the NVMe prefix in their logical name.
        if 'nvme' in str(device):
            return 'NVMe'
        return 'SSD'
    # If the device reports a rotation of 1, it is a spinning device.
    return 'HDD'
# Record the queue depth of the device for determining max number of I/O requests per context switch.
def queue_depth(device):
    # The +1 is to account for the fact that a queue depth of 32 will report as 31 due to off-by-one.
    return str(int(parser("cat", "/sys/block/", device, "/device/queue_depth")) + 1)
# Capture the block size of the device. We can't reliably get this from sysfs so we'll use blockdev.
def block_size(device):
    parsed = parser("sudo blockdev --getbsz", "/dev/", device, "")
    return str(parsed)

# Get number of CPU cores.
def core_count():
    parsed = os.popen('lscpu -e | wc -l').readlines()
    return str(int(next(iter(parsed),None).split('\n')[0]) -1)

# MAIN FUNCTION
if __name__ == '__main__':
    #print "Found " + system['CPU'] + " available cores"
    # Scan for storage devices.
    block_devices = walk('/sys/block/')
    # Pass the results into a list for the test.
    devices = []
    for device in block_devices:
        devices.append(device_attributes(device))
    # Begin the test.
    for device in devices:
        print "******************************"
        print "Detected " + device['name']
        print device['size'] + " available space"
        print "Model name: " + device['model']
        print "Serial Number: " + device['serial']
        print "Firmware Revision: " + device['firmware']
        print "Device type is: " + device['type']
        print "I/O depth of: " + device['queue_depth']
        print "Block size: " + device['block_size'] + " bytes"
        print "Transport model: " + device['interface']
        print "******************************"
    print "Found " + core_count() + " available cores"
    config_file = fio_configurations(devices, core_count(), 'libaio')
    output_format = ' --output-format=json --output=fio-results.json'
    # Run the benchmark
    subprocess.call('sudo fio ' + config_file + '.fio' + output_format, shell=True)