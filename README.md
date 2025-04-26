# esp32s3-ptp

Micropython implementation of USB PTP (picture transfer protocol) for esp32s3.
esp32s3 acts like still image camera to present a simple file-based filesystem
to the host. Filesystem is not block based like FAT so it doesn't need some
"eject" or "clean unmount" before unplugging.

# Linux

Opens the filesystem in file browser window.
it appears like an USB stick.

When gnome is stopped (service gdm3 stop)
PTP filesystem can be accessed
by commandline "gphoto2".

Fileystem could be mounted by gphotofs
which I haven't yet tried.

works:

    browsing directory
    reading file (reads always the same content)
    overwriting file (file content won't change yet)

From gphoto commandline verwriting a file "F1.TXT".

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

For "put" gphoto2 currently responds with "unspecified error -1".

# Windows

windows 10 mostly works!

Directory browsing and file reading is ok.

No errors appear after overwriting file but
overwrite only temporarily deletes file
while on linux the file stays.
