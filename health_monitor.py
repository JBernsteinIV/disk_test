#!/usr/bin/python
# health_monitor.py - Scans for changes to a disk as detected by the system.
# Most changes to a disk's state are handled by smartd, the S.M.A.R.T. daemon.
import os
import csv
from datetime import date
# Scans smartctl for pre-fail attributes of a device. Returns a list of device attribute ID numbers.
def prefail_attributes(device):
    command = "sudo smartctl -ia " + device['name'] + "|grep 'ID#' --after-context=15|grep 'Pre-fail'|awk '{print $1}'"
    prefail_attribute_ids = os.popen(command).readlines()
    attributes = []
    for attribute_id in prefail_attribute_ids:
        attribute = int(attribute_id)
        attributes.append(attribute)
    return attributes
# Capture temperature assertions to see how the temperature changed throughout the test.
def temperature_readings(attributes):
    readings = []
    reading_id = 0
    for entry in attributes:
            if 'Temperature' in str(entry):
                reading = {
                    # Integer number to keep track of how many readings were detected.
                    'id'        : reading_id,
                    # What is the topological name of the device? Remove the [TRANSPORT] from the log.
                    'device'    : str(entry.split('Device: ')[1].split(',')[0]).split(' ')[0],
                    # When did syslog assert the temperature change?
                    'timestamp' : ' '.join(entry.split(' ')[:3]),
                    # What was the previous temperature state at the time of assertion?
                    'prev_temp' : entry.split('changed from')[1].split('to')[0],
                    # What is the new temperature state at the time of assertion? rstrip to remove trailing \n
                    'next_temp' : str(entry.split('changed from')[1].split('to')[1]).rstrip()
                }
                readings.append(reading)
                reading_id += 1
    # Before we return, write the temperature metrics to a CSV file for later use.
    current_date = str(date.today())
    keys = readings[0].keys()
    with open(current_date + '-temperature-metrics.csv', 'wb') as f:
            w = csv.DictWriter(f, keys)
            w.writeheader()
            w.writerows(readings)
    return readings

# Scans /var/log/syslog for smartd assertions.
def check_syslog(context, attribute_ids):
    entries = []
    for attribute_id in attribute_ids:
        command = "sudo cat /var/log/syslog|grep "
        command = command + "'" + context + str(attribute_id) + "'"
        assertions = os.popen(command).readlines()
        for assertion in assertions:
            print assertion
            entries.append(assertion)
    return entries
# Check whether any prefailure attributes increased/decreased during the test.
def passed(attrs):
    syslog_entries = check_syslog('SMART Usage Attribute: ', attrs)
    # Capture any temperature readings during the run of the test.
    temperature_readings(syslog_entries)
    if len(syslog_entries) == 0:
        #print "PASSED"
        return True
    #print "DID NOT PASS"
    return False

def health_monitor(device):
    attrs = prefail_attributes(device)
    passed(attrs)

#check_syslog('SMART Usage Attribute: ', [194])