# esp32s3-ptp

Micropython implementation of USB PTP (picture transfer) protocol for esp32s3.
esp32s3 acts like still image camera to present a simple file-based filesystem
to the host. Filesystem is not block based like FAT so it doesn't need some
"eject" or "clean unmount" before unplugging.

# Linux

Opens the filesystem in file browser window,
appears similar to USB stick.

When gnome is stopped (service gdm3 stop)
PTP filesystem can be accessed
by commandline "gphoto2".

Fileystem could be mounted by
gphotofs which I haven't yet tried.

Browsing directory structure and reading file works.

Writing file has problem. Currently I'm testing overwriting
a file "F1.TXT".

    gphoto2 --shell
    cd /storage_00010001/DIR
    ls
    F1.TXT   F2.TXT
    get F1.TXT
    ok
    put /storage_00010001/DIR/F1.TXT
    unspecified error -1

Note the strange "put" argument. File "F1.TXT" is in
current directory, because it has just been obtained by "get".
But "put" requires full path of target to be specified.

For "put" gphoto2 currently responds with "unspecified error -1".

# Windows

Currently it doesn't work.

After device sends "GetDeviceInfo" windows don't
send any further IN/OUT request to EP1/EP2.
Windows send some control transfers to EP0 though.
