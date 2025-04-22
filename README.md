# esp32s3-ptp

Micropython implementation of USB PTP (picture transfer) protocol for esp32s3.
esp32s3 acts like still image camera to present a simple file-based filesystem
to the host. Filesystem is not block based like FAT.

OS will by default open the filesystem in file browser window and it
looks like USB stick.

On linux PTP filesystem can be accessed by commandline "gphoto2"
or mounted by gphotofs which I haven't yet tried.

Currently there is small issue with writing a file, I think
protocol succeeds but some folder structure has to be correctly
set for file write to succeed without final "unspecified error -1".

Maybe I have to separate packet with OK response, currently
both are sent as one USB packet.

# Windows

Currently it doesn't work.
After device sends "GetDeviceInfo" windows don't
send any further IN/OUT request to EP1/EP2.
Windows send some control transfers to EP0 though.

