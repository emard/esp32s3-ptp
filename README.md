# esp32s3-ptp

Micropython implementation of USB PTP (picture transfer protocol) for esp32s3.
esp32s3 acts like still image camera to present a simple file-based filesystem
to the host. Filesystem is not block based like FAT so it doesn't need some
"eject" or "clean unmount" before unplugging. Tested on linux and windows 10.

# Linux

Opens the filesystem in file browser window.
it appears like an USB stick.

For commandline gnome mounts it here:

    ls /run/user/$UID/gvfs/gphoto2\:host\=iManufacturer_iProduct_iSerial/

$UID is user ID usually starting from 1000.

Fileystem could be mounted by gphotofs
which I haven't yet tried.

When gnome is stopped (service gdm3 stop)
PTP filesystem can be accessed
by commandline "gphoto2".

works:

    browsing folders
    read, write, delete files (including rename, copy, move)

doesn't yet work (TODO):

    create delete folders

# gphoto usage

From gphoto commandline overwriting a file "F1.TXT".

    gphoto2 --shell
    cd /storage_00010001/D1
    ls
    F1.TXT   F2.TXT
    get F1.TXT
    ok
    put /storage_00010001/DIR/F1.TXT

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

Not yet tested
