#!/usr/bin/env python3
#
# Host side of the `usb_simple_device.py` example.  This must be run using standard
# Python on a PC.  See further instructions in `usb_simple_device.py`.

# pip install pyusb

# rmmod ftdi_sio

import sys
import usb.core
import usb.util

# VID and PID of the custom USB device.
#VID = 0x0403
#PID = 0x6010

# to avoid rmmod ftdi_sio
VID = 0x1234
PID = 0xabcd

# USB endpoints used by the device.
# interface 0
I0_EP_IN  = 0x81
I0_EP_OUT = 0x01
I0_EP2_IN = 0x82

# interface 1
I1_EP_IN  = 0x82
I1_EP_OUT = 0x02

# some example control transfers
DFU_SETSTATUS = 2
DFU_GETSTATUS = 3

def main():
  # Search for the custom USB device by VID/PID.
  dev = usb.core.find(idVendor=VID, idProduct=PID)

  if dev is None:
    print("No USB device found")
    sys.exit(1)

  # Claim the USB device.
  usb.util.claim_interface(dev, 0)
#  usb.util.claim_interface(dev, 1)

  # Read the device's strings.
  for i in range(1, 3):
    print(f"str{i}:", usb.util.get_string(dev, i))

  # Test control transfer OUT
  #bmRequestType = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
  bmRequestType = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_DEVICE
  bRequest = DFU_SETSTATUS
  wValue = 0
  wIndex = 0
  data = bytearray([1,2,3,4,5,17])
  timeout = 200
  print(bmRequestType, bRequest, wValue, wIndex, data, timeout)
  if(1):
    ret = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data, timeout)
    print(ret)
  
  # Test control transfer IN
  #bmRequestType = usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
  bmRequestType = usb.util.CTRL_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_DEVICE
  bRequest = DFU_GETSTATUS
  wValue = 0
  wIndex = 0
  wLength = 6
  timeout = 200
  print(bmRequestType, bRequest, wValue, wIndex, wLength, timeout)
  if(0):
    print("getstatus class")
    ret = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, wLength, timeout)
    print(ret)

  bmRequestType = usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
  #bmRequestType = usb.util.CTRL_IN | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_DEVICE
  bRequest = DFU_GETSTATUS
  wValue = 0
  wIndex = 0
  wLength = 6
  timeout = 200
  print(bmRequestType, bRequest, wValue, wIndex, wLength, timeout)
  if(0):
    print("getstatus vendor")
    ret = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, wLength, timeout)
    print(ret)

  # Test control transfer OUT (FT2232 reset - real device answers to this request)
  #bmRequestType = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
  #bRequest = 0
  #wValue = 0
  #wIndex = 0
  #data = None
  #data = bytearray([1,2,3,4,5,17])
  # debug with class instead of vendor, real device doesn't respond to this
  #bmRequestType = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE
  bmRequestType = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_CLASS | usb.util.CTRL_RECIPIENT_DEVICE
  bRequest = DFU_SETSTATUS
  wValue = 0
  wIndex = 0
  data = bytearray([1,2,3,4,5,17])
  timeout = 200
  print(bmRequestType, bRequest, wValue, wIndex, data, timeout)
  if(0):
    ret = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data, timeout)
    print(ret)

  # Test writing to the device.
  ret = dev.write(I0_EP_OUT, b"01234567", timeout=1000)
  print(ret)

  # Test reading from the device.
  print(dev.read(I0_EP_IN, 64))

#  # Test writing to the device.
#  ret = dev.write(I1_EP_OUT, b"01234567", timeout=1000)
#  print(ret)

#  # Test reading from the device.
#  print(dev.read(I1_EP_IN, 64))

  # Release the USB device.
#  usb.util.release_interface(dev, 1)
  usb.util.release_interface(dev, 0)
  usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
