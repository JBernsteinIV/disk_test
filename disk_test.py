#!/usr/bin/python
from datetime import date
from fio_configurations import fio_configurations
import os
import re
import subprocess
import time
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
        'name'          : '/dev/' + device,
        'model'         : model(device),
        'size'          : capacity(device),
        'serial'        : serial_number(device),
        'firmware'      : firmware(device),
        'type'          : device_type(device),
        'interface'     : device_interface(device),
        'queue_depth'   : queue_depth(device),
        'block_size'    : block_size(device),
        'is_raid_device': is_raid_device(device)
    }
    return attributes
# Captures the human-readable model name of the drive.
def model(device):
    return str(parser("cat", "/sys/block/", device, "/device/model"))
# Captures the size of available space; returns size in GB.
def capacity(device):
    amount_in_bytes = int(parser("cat", "/sys/block/", device, "/size")) * 512
    amount_in_gigabytes = amount_in_bytes / (1024 * 1024 * 1024)
    return str(amount_in_gigabytes)
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

# Check for the presence of a RAID controller.
# If one is found, check if the device is connected to a RAID controller.
# TODO: When RAID device is found, return the model name.
# TODO: Separate out this from device Dictionary; make separate function.
# If RAID controller is found, use storcli/perccli utility to find device information.
def is_raid_device(device):
    output = os.popen('lspci|grep -i "RAID"').readlines()
    if not output:
        return "No"
    return str(next(iter(output),None))

def menu(device):
    print "******************************"
    print "Detected " + device['name']
    print "Available Space: " + device['size'] + ' GB'
    print "Model name: " + device['model']
    print "Serial Number: " + device['serial']
    print "Firmware Revision: " + device['firmware']
    #print "Device type is: " + device['type']
    #print "I/O depth of: " + device['queue_depth']
    #print "Block size: " + device['block_size'] + " bytes"
    #print "Transport model: " + device['interface']
    #print "Connected to RAID?: " + device['is_raid_device']
    print "******************************"

def get_system_serial():
    serial = subprocess.check_output("cat /sys/class/dmi/id/product_serial", shell=True)
    return serial.decode('utf-8')

# MAIN FUNCTION
if __name__ == '__main__':
    # Storage server IP
    server = "10.0.8.40:/tmp"

    # Scan for storage devices.
    block_devices = walk('/sys/block/')
    # Pass the results into a list for the test.
    devices = []
    devices_to_test = []
    # This is for SSDs since we won't be stress testing them with fio.
    devices_to_skip = []
    for device in block_devices:
        devices.append(device_attributes(device))
    # Display device information to the user for each device found.
    for device in devices:
        menu(device)
        if device['type'] == 'HDD':
		devices_to_test.append(device)
        else:
        	devices_to_skip.append(device)
    print "Detected " + str(len(devices)) + " amount of drives."
    print "Performing fio test on " + str(len(devices_to_test)) + " drives."
    print "Skipping fio test for " + str(len(devices_to_skip)) + " drives."
    # Build the configuration file for the test. Output to a file with today's timestamp.
    config_file = fio_configurations(devices_to_test, core_count(), 'libaio')
    serial = get_system_serial()
    output_file = str(serial).strip() + "_fio_results_" + str(date.today()) + '.json'
    output_format = ' --output-format=json --output=' + output_file
    additional_flags = ' --norandommap --refill_buffers --timeout=14400'
    # Run the benchmark
    subprocess.call('sudo fio configs.fio ' + output_format + additional_flags, shell=True)
    # Use smartctl for SSDs instead.
    smartctl_output_file = str(serial).strip() + "_smartctl_results_" + str(date.today()) + '.txt'
    for device in devices_to_skip:
	print device['name']
	command = 'sudo smartctl -t short %s' % device['name']
	subprocess.check_output(command, shell=True)
	print "Waiting 120 seconds for smartctl short tests to complete"
	print "Saving smartctl attributes output to %s" % smartctl_output_file
    for device in devices_to_skip:
	subprocess.check_output("smartctl -a %s | tee %s" % (device['name'], smartctl_output_file), shell=True)
        time.sleep(120)
        print "Storage tests completed"
    print "Uploading %s to storage server" % server
    uploading = subprocess.check_output("sshpass scp -o StrictHostKeyChecking=no %s root@%s" % (output_file, server), shell=True)
    uploading.decode('utf-8')
