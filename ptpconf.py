# file browser using USB PTP/MTP protocol
# should work on linux, windows, apple
# linux gvfs BUG: MTP can write but can't read
# file r/w works on gvfs with PTP:
# if interface is named "MTP", host uses MTP protocol.
# for any other name host uses PTP protocol.
#PROTOCOL=b"PTP" # libgphoto2, windows and linux
PROTOCOL=b"MTP" # libmtp, windows and apple, linux write but not read
