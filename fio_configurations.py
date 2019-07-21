#!/usr/bin/python
from datetime import date

def fio_configurations(devices, core_count, engine):
    filename = "disk-test-" + str(date.today())
    # Global configurations
    with open('./' + filename + '.fio', 'w+') as configurations:
        configurations.write('[global]\n')
        # In case we want to use a different engine.
        configurations.write('ioengine=' + engine + '\n')
        # Enable O_DIRECT to bypass page cache.
        configurations.write('direct=1\n')
        configurations.write('rw=read\n')
        # Determines number of cores to allocate per device.
        processes_per_job = int(core_count) // len(devices)
        # Builds configurations for each device.
        for device in devices:
            configurations.write('[job ' + device['name'] + ' ]\n')
            configurations.write('filename=' + device['name'] + '\n')
            configurations.write('bs=' + device['block_size'] + '\n')
            configurations.write('iodepth=' + device['queue_depth'] + '\n')
            configurations.write('numjobs=' + str(processes_per_job) + '\n')
            configurations.write('size=2g\n')
    return filename