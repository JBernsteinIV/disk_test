# disk_test - Requires fio (Flexible I/O Tester)
This utility creates a fio configuration file based off of information from /sys/block.

/sys/ is chosen because it provides the most raw device information the kernel will expose to the application space.

The main important element of the utility is the device_attributes() Dictionary object that gets returned.

	def device_attributes(device):
	    attributes = {
        'name'          : '/dev/' + device, //e.g. /dev/sda, /dev/sdb, etc.
        'model'         : model(device),  // What is the model name of the hard drive?
        'size'          : capacity(device),// How much storage is available?
        'serial'        : serial_number(device), //Self-explanatory.
        'firmware'      : firmware(device), //What is the firmware revision of the device?
        'type'          : device_type(device), //Is it an HDD, SSD, or NVMe? (PCI-e SSD)
        'interface'     : device_interface(device), //Is it SATA, PCI-e, SAS, etc?
        'queue_depth'   : queue_depth(device), //How many I/O operations can occur in x seconds?
        'block_size'    : block_size(device), //Typically returns the value 4096 (page size).
        'is_raid_device': is_raid_device(device) //Is the drive connected to a RAID controller?
    }
    return attributes
# Queue Depth or "I/O Depth"
Queue depth refers to the amount of I/O requests that can be submitted to a device and fulfilled by a device within a second. Traditional SATA drives typically support a maximum of 32 which means that in peak performance, the drive can fulfill 32 I/O operations per second (32 IOPS). Serial Attached SCSI or 'SAS' typically can handle 128 IOPS at peak performance. And theoretically at peak performance, an NVMe drive can handle 65,536 I/O operations per second (in reality they are typically hovering at 128 I/O operations per second).
# SAS vs. SATA - How to distinguish the two?
If you run 'lsblk' on a system with SAS drives versus SATA drives, the two would look identical.
In /sys/block/<sda/sdb/etc>/device/ lies a file called 'wwid' or World-Wide ID. SAS drives typically come equipped with a 'SAS Address' which is global and maintained by the Network Address Authority or 'naa'.

If the device is a SAS drive, the file will begin with 'naa.' and is followed by the SAS address. If the file is a SATA drive, it will  begin with 't10.ata' where T10 refers to the name of the committee who built and authorized the Serial ATA protocol. The rest of the file will include the device model name and the device serial number.

NVMe drives can be relied upon by their naming convention '/dev/nvme'. The NVMe protocol requires that the devices show up with the name to distinguish PCI-e SSDs from their SATA or SAS counterparts. As such, we can determine that a drive is an NVMe drive if the word 'nvme' shows up in the device name.

# RAID Controllers or 'Hard RAID'
RAID controllers will hide the existence of the drives until a 'Virtual Drive' (VD) is created that the disk is a part of. This utility primarily works with LSI/Avago/Broadcom RAID controllers and relies upon the 'storcli' utility provided by Broadcom.
Information on drives behind a RAID controller cannot be relied upon by sysfs and instead it is easier and more efficient to use the storcli utility (or 'perccli' for  Dell EMC's brand of 'PowerEdge RAID Controllers').
Individual drive information can be accessed from storcli or perccli by grabbing the Enclosure ID or 'EID' of the RAID controller and then targeting the slot number of the drive.
    
    Example: ./storcli64 /c0/e252/s0 locate # Here the Enclosure ID (EID) is '252'.
**Creating a Virtual Drive**
		

    Example: ./storcli64 add vd type=raid10 drives=252:0-4 pdperarray=2 wt
**Checking Backup Battery Unit Status**

    ./storcli64 /c0/bbu show # If status returns 'Failure', BBU is absent

 - A 'BBU' is used to temporarily continue to supply power to a RAID controller to allow last-moment I/O to be saved to disk in the event of power loss to the system.
 - Generally speaking, it is best to put the RAID array into 'Write Back' mode in the presence of a BBU. This means the RAID controller will take all I/O operations and write them to an internal cache and will then write the data to disk when the cache is full. Alternatively, 'Write Through' mode is also an option which means the cache is seldomly used and instead all I/O goes directly to disk.
# Why fio? - Most flexible stress test for any I/O.
fio is maintained and created by Jens Axboe, the current maintainer of the 'Block I/O Layer' in the Linux kernel. Jens created the utility to make an easier-to-use stress testing utility for the various kinds of I/O devices he began to work with. This utility has an incredible amount of features which you can learn more about here: [https://fio.readthedocs.io/en/latest/](https://fio.readthedocs.io/en/latest/)
