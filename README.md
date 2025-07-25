# esp32s3-ptp

Micropython implementation of USB PTP (picture transfer protocol) for esp32s3.
esp32s3 acts like still image camera to present a simple file-based filesystem
to the host. Filesystem is not block based like FAT so it doesn't need some
"eject" or "clean unmount" before unplugging. Tested on linux and windows 10.

# Install

   mpremote resume cp ptp.py :/

autostart

   echo "import ptp" > boot.py
   mpremote resume cp boot.py :/

# Linux

Open Gnome file browser "nautilus" by clicking
on blue drawer icon. PTP device should appear
on the left side of the window.

If PTP device doesn't appear, maybe "gvfs"
should be installed. Then click again
on blue drawer icon.

    apt install gvfs
    pkill gvfs; pkill nautilus

gvfs 1.57.2 has bug with MTP so currently it
is recommended to use PTP protocol rather
than MTP.

    PROTOCOL=b"PTP"

PTP:  completely works and directory browsing is
faster than MTP.

MTP: gvfs read does not work but write works.
gvfs claims device with libmtp. If file read
was done by libmtp it would work, but instead
of libmtp, gvfs tries to claim device
with libphoto2 to reading the file, while
device is already claimed by libmtp. Only
one process (either libmtp or libgphoto2)
can claim device but not both at the same time
so from this situation the error appears.

For commandline and scripting:
when user is logged to gnome, PTP is mounted here:

    ls /run/user/$UID/gvfs/gphoto2\:host\=iManufacturer_iProduct_00000000/

$UID is user ID usually starting from 1000.

Fileystem could be mounted by gphotofs
which I haven't yet tried.

When gnome is stopped (service gdm3 stop)
PTP filesystem can be accessed
by commandline "gphoto2".

# mpremote usage

"ptp.py" implements usb-serial CDC micropython prompt.
File operations with mpremote should be used with "resume"
option like this

    mpremate resume ls
    mpremote resume cp file1.txt :/

Without "resume" mpremote will not work.
mpremote first performs soft-reset which disconnects
usb-serial device and then a full screen of python
errors will appear.

# gphoto usage

From gphoto commandline overwriting a file "F1.TXT".

    gphoto2 --shell
    cd /store_00010001/D1
    ls
    F1.TXT   F2.TXT
    get F1.TXT
    ok
    put /store_00010001/DIR/F1.TXT

Note the strange "put" argument. File "F1.TXT" is in
current directory, because it has just been obtained by "get".
But "put" requires full path of target to be specified.

# Windows

Opens the filesystem in file browser window.
it appears like an USB stick.

Similar as linux, only difference is that in
windows the storage name appears first while
linux skips storage name and displays root folder.

# Apple

Early support tested on Sonoma 14.4.
Set interface to MTP mode:

    PROTOCOL=b"MTP" # libmtp, windows and apple

After plugging device to USB port a window should
appear with vfs file list and tabs for storages
"vfs" and "custom" in top area of the window.

If protocol freezes then we have some bugs...

# Android

It works in android (MTP mode currently tested).

# MTP mode

If USB interface is named "MTP" then this device
will be treated as MTP instead of PTP. To try it
edit source "ptp.py".

    INTERFACE0=b"MTP"

"ptp.py" handles PTP and MTP the same and
on windows 10 it works the same.

on linux MTP is handled by libmtp while PTP is
handled by libgphoto2

from linux gnome MTP browsing, write,
delete works but reading files doesn't work.
Attept to read file from gnome reports
"Errno 95 Operation Not Supported".

It is because gnome tries to open USB device
from gphoto2 while same device is already
claimed by MTP.

As issue #801 with subject
"gvfs MTP can write file but can't read it"
it is reported to
https://gitlab.gnome.org/GNOME/gvfs/-/issues/801

It is because on linux gvfs MTP first tries
to read file using 0x101B GetPartialObject
and if it isn't implemented it should
use 0x1009 GetObject. If 0x101B is not supported,
then gvfs mtp mode tries to claim device with libgphoto2
which not possible because device is already
claimed with libmtp() so this attempt to read fails.

Early support for 0x101B GetPartialObject is here
but it works only for small files under 4K length.

Getting debug logs from linux gnome

See https://wiki.gnome.org/Projects(2f)gvfs(2f)debugging.html

Terminate all gvfs daemons and the client application you use (e.g. Nautilus) at first:

    pkill gvfs; pkill nautilus

(Be careful, this step will terminate also your pending file operations.)
Start main daemon with enabled debug level 9 output:

    GVFS_DEBUG=9 $(find /usr/lib* -name gvfsd 2>/dev/null) --replace 2>&1 | tee gvfsd.log

You can use additional environment variables in special cases, e.g.:

    GVFS_SMB_DEBUG=10 GVFS_DEBUG=9 $(find /usr/lib* -name gvfsd 2>/dev/null) --replace 2>&1 | tee gvfsd.log

Reproduce your problem.
Terminate gvfs daemons after that.

    pkill gvfs

(GVfs will operate as usual after this step.)

Trying mtp alone

    apt install mtp-tools
    pkill gvfs; pkill nautilus
    mtp-files
    File ID: 11
        Filename: sdpin.py
        File size 189 (0x00000000000000BD) bytes
        Parent ID: 0
        Storage ID: 0x00010001
        Filetype: Text file

    mtp-getfile 0 11 sdpin.py
    libmtp version: 1.1.22

    Device 0 (VID=1234 and PID=abcd) is UNKNOWN in libmtp v1.1.22.
    Please report this VID/PID and the device model to the libmtp development team
    Getting file/track 11 to local file sdpin.py
    Progress: 205 of 205 (100%)
