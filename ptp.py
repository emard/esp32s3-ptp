# esp32s3 micropython >= 1.24

# file browser using USB PTP protocol
# tested on linux gnome and windows 10

# protocol info:
# git clone https://github.com/gphoto/libgphoto2
# cd libgphoto2/camlibs/ptp2
# files ptp-pack.c ptp.c ptp.h
# https://github.com/gphoto/libgphoto2/tree/master/camlibs/ptp2
# https://github.com/capaulson/pyptp
# https://forum.arduino.cc/t/using-ptp-to-control-camera-on-m0-board/898849

# Implementation of a very simple, custom USB device in Python.  The device has an
# IN and OUT endpoint and interrupt IN.
#
# To run, just execute this file on a device with
# machine.USBDevice support,
# this is just fresh enough micropython binary.
# connected with usb-serial to see serial debug prints
#
# $ mpremote cp ptp.py :/
# $ mpremote
# >>> <enter>
# >>> <ctrl-d>
# device soft-reset
# >>> import ptp
#
# The device will then change to the custom USB device.
#
# for debugging if you change USB class to vendor
# specific (255) OS will not claim the device so
# user-space test can run
#
# $ python hostptp.py
#
# You'll need to have `pyusb` installed via
# `pip install pyusb` to run the host PC code.
# udev rule is needed for user
# to access the custom USB device.

import machine, struct, time, os
#import ecp5
from micropython import const

# VID and PID of the USB device.
#VID = const(0x0403)
#PID = const(0x6010)

# to avoid loading ftdi_sio
VID = const(0x1234)
PID = const(0xabcd)

# Endpoint 0 for setup
#EP0_IN    = 0x80
#EP0_OUT   = 0x01

# USB endpoints used by the device.
# interface 0
I0_EP1_IN=const(0x81)
I0_EP1_OUT=const(0x01)
I0_EP2_IN=const(0x82)

# device textual appearance
MANUFACTURER=b"iManufacturer"
PRODUCT=b"iProduct"
SERIAL=b"iSerial"
CONFIGURATION=b"iConfiguration"
INTERFACE0=b"iInterface0"
INTERFACE1=b"iInterface1"
VERSION=b"3.1.8"
STORAGE=b"iStorage"
VOLUME=b"iVolume"

# PTP
# USB Still Image Capture Class defines
USB_CLASS_IMAGE=const(6)
STILL_IMAGE_SUBCLASS=const(1) # still image cam
STILL_IMAGE_PROTOCOL=const(1)

# no driver loaded, vendor-spec to avoid
# loading of system default drivers during debug
#USB_CLASS_IMAGE=const(255)
#STILL_IMAGE_SUBCLASS=const(255)
#STILL_IMAGE_PROTOCOL=const(255)

# Class-Specific Requests - bRequest values
STILL_IMAGE_CANCEL_REQUEST=const(0x64)
STILL_IMAGE_GET_EXT_EVENT_DATA=const(0x65)
STILL_IMAGE_DEV_RESET_REQ=const(0x66)
STILL_IMAGE_GET_DEV_STATUS=const(0x67)

# USB device descriptor.
_desc_dev = bytes([
0x12,  # 0 bLength
0x01,  # 1 bDescriptorType: Device
0x00,  # 2
0x02,  # 3 USB version: 2.00
0x00,  # 4 bDeviceClass: defined at interface level
0x00,  # 5 bDeviceSubClass
0x00,  # 6 bDeviceProtocol
0x40,  # 7 bMaxPacketSize
VID & 0xFF, # 8
VID >> 8 & 0xFF,  # 9 VID
PID & 0xFF, # 10
PID >> 8 & 0xFF,  # 11 PID
0x00,  # 12
0x07,  # 13 bcdDevice: 7.00
0x01,  # 14 iManufacturer
0x02,  # 15 iProduct
0x03,  # 16 iSerialNumber
0x01,  # 17 bNumConfigurations: 1
])

# USB configuration descriptor.
_desc_cfg = bytes([
# Configuration Descriptor.
0x09,  # 0 bLength
0x02,  # 1 bDescriptorType: configuration
0x27,  # 2
0x00,  # 3 wTotalLength: 39
0x01,  # 4 bNumInterfaces
0x01,  # 5 bConfigurationValue
0x04,  # 6 iConfiguration
0x80,  # 7 bmAttributes = Bus powered
0x96,  # 8 bMaxPower
# Interface Descriptor.
0x09,  # 0 bLength
0x04,  # 1 bDescriptorType: interface
0x00,  # 2 bInterfaceNumber
0x00,  # 3 bAlternateSetting
0x03,  # 4 bNumEndpoints
USB_CLASS_IMAGE,  # 5 bInterfaceClass = imaging
STILL_IMAGE_SUBCLASS,  # 6 bInterfaceSubClass
STILL_IMAGE_PROTOCOL,  # 7 bInterfaceProtocol
0x05,  # 8 iInterface
# Interface 0 Bulk Endpoint OUT
0x07,  # 0 bLength
0x05,  # 1 bDescriptorType: endpoint
I0_EP1_IN,  # 2 bEndpointAddress
0x02,  # 3 bmAttributes: bulk
0x40,  # 4
0x00,  # 5 wMaxPacketSize
0x00,  # 6 bInterval
# Interface 0 Bulk Endpoint IN.
0x07,  # 0 bLength
0x05,  # 1 bDescriptorType: endpoint
I0_EP1_OUT,  # 2 bEndpointAddress
0x02,  # 3 bmAttributes: bulk
0x40,  # 4
0x00,  # 5 wMaxPacketSize
0x00,  # 6 bInterval
# Interface 0 Interrupt Endpoint IN.
0x07,  # 0 bLength
0x05,  # 1 bDescriptorType: endpoint
I0_EP2_IN,  # 2 bEndpointAddress
0x03,  # 3 bmAttributes: interrupt
0x40,  # 4
0x00,  # 5 wMaxPacketSize
0x01,  # 6 bInterval
])

# USB strings.
_desc_strs = {
1: MANUFACTURER,
2: PRODUCT,
3: SERIAL,
4: CONFIGURATION,
5: INTERFACE0,
6: INTERFACE1,
}
# USB constants for bmRequestType.
USB_REQ_RECIP_INTERFACE = 0x01
USB_REQ_RECIP_DEVICE = 0
USB_REQ_TYPE_CLASS = 0x20
USB_REQ_TYPE_VENDOR = 0x40
USB_DIR_OUT = 0x00
USB_DIR_IN = 0x80

# some USB CTRL commands (FIXME)
SETSTATUS = 2
GETSTATUS = 3
status = bytearray([0,0,0,0,0,0])

# global PTP session ID, Transaction ID, opcode
sesid=0
txid=0
opcode=0

# global sendobject (receive file) length
send_parent=0 # to which directory we will send object
send_parent_path="/"
send_length=0
remaining_send_length=0
remain_getobj_len=0
fd=None # local open file descriptor

# for ls() generating vfs directory tree
# global handle incremented
next_handle=0
path2handle={}
handle2path={}
dir2handle={}
current_send_handle=0

# for given object handle "oh" find it's parent
# actually a handle of directory which
# holds this file
def parent(oh):
  path=handle2path[oh]
  if path[-1]=="/" and path!="/":
    dirname=path[:path[:-1].rfind("/")+1]
  else:
    dirname=path[:path.rfind("/")+1]
  return path2handle[dirname][0]

# get list of objects from directory handle "dh"
def objects(dh):
  return list(path2handle[handle2path[dh]].values())[1:]

def basename(oh):
  fullname=handle2path[oh]
  if fullname=="/":
    return "/"
  if fullname[-1]=="/":
    return fullname[fullname[:-1].rfind("/")+1:-1]
  return fullname[fullname.rfind("/")+1:]

# path: full path string
# recurse: number of subdirectorys to recurse into
def ls(path,recurse):
  global next_handle
  try:
    dir=os.ilistdir(path)
  except:
    return
  # if path doesn't trail with slash, add slash
  if path[-1]!="/":
    path+="/"
  # path -> handle and handle -> path
  # "/lib" in {}
  if path in path2handle:
    current_dir=path2handle[path][0]
  else:
    current_dir=next_handle
    next_handle+=1
    path2handle[path]={0:current_dir}
    handle2path[current_dir]=path
  # id -> directory list
  if not current_dir in dir2handle:
    dir2handle[current_dir]={}
  for obj in dir:
    objname=obj[0]
    fullpath=path+objname
    if objname in path2handle[path]:
      current_handle=path2handle[path][objname]
    else:
      current_handle=next_handle
      next_handle+=1
    if obj[1]==16384: # obj[1]==DIR
      print(path,"DIR:",obj)
      if recurse>0:
        newhandle=ls(fullpath,recurse-1)
        dir2handle[current_dir][newhandle]=obj
        objname_=objname+"/"
        if not objname_ in path2handle[path]:
          path2handle[path][objname_]=newhandle
    else: # obj[1]==FILE
      dir2handle[current_dir][current_handle]=obj
      print(path,"FILE:",obj)
      if not objname in path2handle[path]:
        path2handle[path][objname]=current_handle
        handle2path[current_handle]=fullpath
  return current_dir

# USB PTP "type" 16-bit field
PTP_USB_CONTAINER_UNDEFINED=const(0)
PTP_USB_CONTAINER_COMMAND=const(1)
PTP_USB_CONTAINER_DATA=const(2)
PTP_USB_CONTAINER_RESPONSE=const(3)
PTP_USB_CONTAINER_EVENT=const(4)

# PTP v1.0 response codes
PTP_RC_Undefined=const(0x2000)
PTP_RC_OK=const(0x2001)
PTP_RC_GeneralError=const(0x2002)
PTP_RC_SessionNotOpen=const(0x2003)
PTP_RC_InvalidTransactionID=const(0x2004)
PTP_RC_OperationNotSupported=const(0x2005)
PTP_RC_ParameterNotSupported=const(0x2006)
PTP_RC_IncompleteTransfer=const(0x2007)
PTP_RC_InvalidStorageId=const(0x2008)
PTP_RC_InvalidObjectHandle=const(0x2009)
PTP_RC_DevicePropNotSupported=const(0x200A)
PTP_RC_InvalidObjectFormatCode=const(0x200B)
PTP_RC_StoreFull=const(0x200C)
PTP_RC_ObjectWriteProtected=const(0x200D)
PTP_RC_StoreReadOnly=const(0x200E)
PTP_RC_AccessDenied=const(0x200F)
PTP_RC_NoThumbnailPresent=const(0x2010)
PTP_RC_SelfTestFailed=const(0x2011)
PTP_RC_PartialDeletion=const(0x2012)
PTP_RC_StoreNotAvailable=const(0x2013)
PTP_RC_SpecificationByFormatUnsupported=const(0x2014)
PTP_RC_NoValidObjectInfo=const(0x2015)
PTP_RC_InvalidCodeFormat=const(0x2016)
PTP_RC_UnknownVendorCode=const(0x2017)
PTP_RC_CaptureAlreadyTerminated=const(0x2018)
PTP_RC_DeviceBusy=const(0x2019)
PTP_RC_InvalidParentObject=const(0x201A)
PTP_RC_InvalidDevicePropFormat=const(0x201B)
PTP_RC_InvalidDevicePropValue=const(0x201C)
PTP_RC_InvalidParameter=const(0x201D)
PTP_RC_SessionAlreadyOpened=const(0x201E)
PTP_RC_TransactionCanceled=const(0x201F)
PTP_RC_SpecificationOfDestinationUnsupported=const(0x2020)
# PTP v1.1 response codes
PTP_RC_InvalidEnumHandle=const(0x2021)
PTP_RC_NoStreamEnabled=const(0x2022)
PTP_RC_InvalidDataSet=const(0x2023)

# return: length,type,code,trans_id
# print("%08x %04x %04x %08x" % unpack_ptp_hdr(ptp_container))
def unpack_ptp_hdr(cnt):
  return struct.unpack("<LHHL",cnt)

def print_ptp_header(cnt):
  print("%08x %04x %04x %08x" % unpack_ptp_hdr(cnt),end="")

def print_ptp_params(cnt):
  for i in range((len(cnt)-12)//4):
    print("p%d:%08x" % (i,struct.unpack("<L",cnt[12+4*i:16+4*i])[0]))

def print_ptp(cnt):
  print_ptp_header(cnt)
  print_ptp_params(cnt)

def print_hex(cnt):
  print_ptp_header(cnt)
  for x in cnt[12:]:
    print(" %02x" % x,end="")
  print("")

def print_hexdump(cnt):
  for x in cnt:
    print(" %02x" % x,end="")
  print("")

def print_ucs2_string(s):
  #l,=struct.unpack("<B",s[0])
  for i in range(s[0]):
    print("%c" % s[1+i+i],end="")
  print("")

# params 0..5
def PTP_CNT_INIT(cnt,type,code,*params):
  length=12+4*len(params)
  cnt[0:12]=struct.pack("<LHHL",length,type,code,txid)
  for i in range(len(params)):
    cnt[12+i*4:16+i*4]=struct.pack("<L",params[i])
  return length

# data payload
def PTP_CNT_INIT_DATA(cnt,type,code,data):
  length=12+len(data)
  cnt[0:12]=struct.pack("<LHHL",length,type,code,txid)
  cnt[12:length]=data
  return length

def PTP_CNT_INIT_LEN_DATA(cnt,length,type,code,data):
  cnt[0:12]=struct.pack("<LHHL",length,type,code,txid)
  cnt[12:length]=data
  return length

def Undefined(cnt):
  print("undefined opcode")

#def unpack_type(cnt):
#  return struct.unpack("<H",cnt[4:6])[0]

#def unpack_opcode(cnt):
#  return struct.unpack("<H",cnt[6:8])[0]

#def unpack_txid(cnt):
#  return struct.unpack("<L",cnt[8:12])[0]


# DeviceInfo pack/unpack
#PTP_di_StandardVersion=const(0)
#PTP_di_VendorExtensionID=const(2)
#PTP_di_VendorExtensionVersion=const(6)
#PTP_di_VendorExtensionDesc=const(8)
#PTP_di_FunctionalMode=const(8)
#PTP_di_Operations=const(10)

# pack a tuple as 16-bit array for deviceinfo
def uint16_array(a):
  return struct.pack("<L"+"H"*len(a),len(a),*a)

# pack a bytearray string as 16-bit ucs2 string for device info
def ucs2_string(s):
  if len(s):
    return struct.pack("<B"+"H"*len(s),len(s),*s)
  return b"\0"

def decode_ucs2_string(s):
  len=s[0]
  str=bytearray(len)
  for i in range(len):
    str[i]=s[1+i+i]
  return str

def get_ucs2_string(s):
  len=s[0]
  return s[0:1+len+len]

# objecthandle array
def uint32_array(a):
  return struct.pack("<L"+"L"*len(a),len(a),*a)

# send_name=ucs2_string(b"F1.TXT\0") # initialize file name in d1 directory

length_response=bytearray(1) # length to send response once
send_response=bytearray(32) # response to send

length_irq_response=bytearray(1) # length to send response once
send_irq_response=bytearray(32) # interrupt response to send

# after one IN submit another with response OK
def respond_ok():
  length_response[0] = PTP_CNT_INIT(send_response,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK)
  # length is set now and reset to 0 after
  # send is scheduled

def OpenSession(cnt):
  global txid,sesid,opcode
  #print("OpenSession")
  #print("<",end="")
  #print_hex(cnt)
  txid,sesid=struct.unpack("<LL",cnt[8:16])
  #print("txid=",txid,"sesid=",sesid)
  # prepare response 0c 00 00 00  03 00  01 20  00 00 00 00
  #ptp_response_offset=0
  #ptp_response_length=0
  # ptp_response_data[:ptp_response_length]=bytearray(4) # array of 0
  #length=next_ptp_response_data(cnt)
  length=PTP_CNT_INIT(i0_usbd_buf,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK)
  #print(">",end="")
  #print_hex(i0_usbd_buf)
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

# more codes in
# git clone https://github.com/gphoto/libgphoto2
# cd libgphoto2/camlibs/ptp2/ptp.h
# events
PTP_EC_CancelTransaction=const(0x4001)
PTP_EC_ObjectInfoChanged=const(0x4007)

# device properties
PTP_DPC_DateTime=const(0x5011)
# image formats 
PTP_OFC_Undefined=const(0x3000)
PTP_OFC_Directory=const(0x3001)
PTP_OFC_Defined=const(0x3800)
PTP_OFC_Executable=const(0x3003)
PTP_OFC_Text=const(0x3004)
PTP_OFC_HTML=const(0x3005)
PTP_OFC_WAV=const(0x3008)
PTP_OFC_EXIF_JPEG=const(0x3801)
PTP_OFC_BMP=const(0x3804)
PTP_OFC_Undefined_0x3806=const(0x3806)
PTP_OFC_GIF=const(0x3807)
PTP_OFC_JFIF=const(0x3808)
PTP_OFC_PNG=const(0x380B)
PTP_OFC_Undefined_0x380C=const(0x380C)
PTP_OFC_TIFF=const(0x380D)

def GetDeviceInfo(cnt):
  global txid,opcode
  print("GetDeviceInfo")
  print("<",end="")
  print_hex(cnt)
  _,_,opcode,txid=unpack_ptp_hdr(cnt)
  # opcode 0x1001
  # prepare response: device info standard 1.00 = 100
  header=struct.pack("<HLH", 100, 6, 100)
  extension=b"\0"
  #extension=ucs2_string(b"microsoft.com: 1.0\0")
  functional_mode=struct.pack("<H", 0) # 0: standard mode
  #operations=uint16_array(list((ptp_opcode_cb.keys()))) # human readable
  operations=uint16_array(ptp_opcode_cb) # short of previous line
  events=uint16_array((PTP_EC_ObjectInfoChanged,))
  deviceprops=uint16_array((PTP_DPC_DateTime,))
  captureformats=uint16_array((PTP_OFC_EXIF_JPEG,))
  imageformats=uint16_array((
  PTP_OFC_Undefined,
  PTP_OFC_Directory,
  PTP_OFC_Text,
  PTP_OFC_HTML,
  PTP_OFC_EXIF_JPEG,
  PTP_OFC_WAV,
  PTP_OFC_Defined,))
  manufacturer=ucs2_string(MANUFACTURER+b"\0")
  model=ucs2_string(PRODUCT+b"\0")
  deviceversion=ucs2_string(VERSION+b"\0")
  serialnumber=ucs2_string(SERIAL+b"\0")
  data=header+extension+functional_mode+operations+events+deviceprops+captureformats+imageformats+manufacturer+model+deviceversion+serialnumber
  length=PTP_CNT_INIT_DATA(i0_usbd_buf,PTP_USB_CONTAINER_DATA,opcode,data)
  respond_ok()
  print(">",end="")
  print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

def GetStorageIDs(cnt):
  global txid,opcode
  print("GetStorageIDs")
  print("<",end="")
  print_hex(cnt)
  _,_,opcode,txid=unpack_ptp_hdr(cnt)
  # opcode 0x1004
  # prepare response
  # actually a PTP array
  # first 32-bit is length (number of elements, actually storage drives)
  # rest are elements of 32-bits
  # each element can be any unique integer
  # actually a storage drive id
  data=uint32_array([0x10001])
  length=PTP_CNT_INIT_DATA(i0_usbd_buf,PTP_USB_CONTAINER_DATA,opcode,data)
  respond_ok()
  print(">",end="")
  print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

# PTP_si_StorageType               0
# PTP_si_FilesystemType            2
# PTP_si_AccessCapability          4
# PTP_si_MaxCapability             6
# PTP_si_FreeSpaceInBytes         14
# PTP_si_FreeSpaceInImages        22
# PTP_si_StorageDescription       26

# Storage Types
STORAGE_FIXED_RAM=const(1)
STORAGE_REMOVABLE_RAM=const(2)
STORAGE_REMOVABLE_ROM=const(3)
STORAGE_FIXED_ROM=const(4)
STORAGE_REMOVABLE_MEDIA=const(5)
STORAGE_FIXED_MEDIA=const(6)

# Filesystem Access Capability
STORAGE_READ_WRITE=const(0)
STORAGE_READ_ONLY_WITHOUT_DELETE=const(1)
STORAGE_READ_ONLY_WITH_DELETE=const(2)

def GetStorageInfo(cnt):
  global txid,opcode
  print("GetStorageInfo")
  print("<",end="")
  print_hex(cnt)
  _,_,opcode,txid=unpack_ptp_hdr(cnt)
  # opcode 0x1005
  # prepare response
  StorageType=STORAGE_FIXED_MEDIA
  FilesystemType=2
  AccessCapability=STORAGE_READ_WRITE
  storinfo=os.statvfs("/")
  blksize=storinfo[0]
  blkmax=storinfo[2]
  blkfree=storinfo[3]
  MaxCapability=blksize*blkmax
  FreeSpaceInBytes=blksize*blkfree
  FreeSpaceInImages=0x10000
  StorageDescription=ucs2_string(STORAGE+b"\0")
  VolumeLabel=ucs2_string(VOLUME+b"\0")
  hdr=struct.pack("<HHHQQL",StorageType,FilesystemType,AccessCapability,MaxCapability,FreeSpaceInBytes,FreeSpaceInImages)
  data=hdr+StorageDescription+VolumeLabel
  length=PTP_CNT_INIT_DATA(i0_usbd_buf,PTP_USB_CONTAINER_DATA,opcode,data)
  respond_ok()
  print(">",end="")
  print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

# for given handle id of a directory
# returns array of handles
def GetObjectHandles(cnt):
  global txid,opcode
  print("GetObjectHandles")
  print("<",end="")
  print_hex(cnt)
  _,_,opcode,txid=unpack_ptp_hdr(cnt)
  # opcode 0x1007
  # unpack 3 parameters
  p1,p2,p3=struct.unpack("<LLL",cnt[12:24])
  print("p1=%08x p2=%08x p3=%08x" % (p1,p2,p3))
  # prepare response depending on p1-3 parameters
  dirhandle=p3
  if p3==0xFFFFFFFF or p3==0x10001: # root directory
    dirhandle=0
  ls(handle2path[dirhandle],1)
  data=uint32_array(objects(dirhandle))
  # FIXME when directory has many entries > 256 data
  # would not fit in one 1024 byte block
  # block continuation neede
  length=PTP_CNT_INIT_DATA(i0_usbd_buf,PTP_USB_CONTAINER_DATA,opcode,data)
  respond_ok()
  print(">",end="")
  print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

# PTP_oi_StorageID		 0
# PTP_oi_ObjectFormat		 4
# PTP_oi_ProtectionStatus        6
# PTP_oi_ObjectSize		 8
# PTP_oi_ThumbFormat		12
# PTP_oi_ThumbSize		14
# PTP_oi_ThumbPixWidth		18
# PTP_oi_ThumbPixHeight		22
# PTP_oi_ImagePixWidth		26
# PTP_oi_ImagePixHeight		30
# PTP_oi_ImageBitDepth		34
# PTP_oi_ParentObject           38
# PTP_oi_AssociationType        42
# PTP_oi_AssociationDesc        44
# PTP_oi_SequenceNumber		48
# PTP_oi_filenamelen		52
# PTP_oi_Filename               53

def GetObjectInfo(cnt):
  global txid,opcode
  print("GetObjectInfo")
  print("<",end="")
  print_hex(cnt)
  _,_,opcode,txid=unpack_ptp_hdr(cnt)
  #txid=unpack_txid(cnt)
  # opcode 0x1008
  p1,=struct.unpack("<L",cnt[12:16])
  print("p1=%08x" % p1)
  StorageID=0x10001
  ObjectFormat=PTP_OFC_Text
  ProtectionStatus=0
  #ObjectSize=0
  thumb_image_null=bytearray(26)
  ParentObject=0
  assoc_seq_null=bytearray(10)
  length=0 # zero response currently
  if p1 in handle2path:
    fullpath=handle2path[p1]
    print(fullpath)
    ParentObject=parent(p1) # 0 means this file is in root directory
    (objname,objtype,_,objsize)=dir2handle[ParentObject][p1]
    #stat=os.stat(fullpath)
    #objname=basename(p1)
    #if handle2path[p1][-1]=="/":
    if objtype==16384: # dir
      ObjectFormat=PTP_OFC_Directory
      ObjectSize=0
    else: # stat[0]=32768 # file
      ObjectFormat=PTP_OFC_Text
      ObjectSize=objsize
    hdr1=struct.pack("<LHHL",StorageID,ObjectFormat,ProtectionStatus,ObjectSize)
    hdr2=struct.pack("<L",ParentObject)
    #print("objname:",objname)
    name=ucs2_string(objname.encode()) # directory name converted
    #year, month, day, hour, minute, second, weekday, yearday = time.localtime()
    # create/modify report as current date (file constantly changes date)
    create=b"\0" # if we don't provide file time info
    #create=ucs2_string(b"%04d%02d%02dT%02d%02d%02d\0" % (year,month,day,hour,minute,second))
    #create=ucs2_string(b"20250425T100120\0") # 2025-04-25 10:01:20
    modify=create
    #data=hdr1+thumb_image_null+hdr2+assoc_seq_null+name+b"\0\0\0"
    data=hdr1+thumb_image_null+hdr2+assoc_seq_null+name+create+modify+b"\0"
    #data=header+name+b"\0\0\0"
    length=PTP_CNT_INIT_DATA(i0_usbd_buf,PTP_USB_CONTAINER_DATA,opcode,data)
    respond_ok()
  if length==0: # p1 objecthandle not found, report just ok
    length=PTP_CNT_INIT(i0_usbd_buf,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK)
  print(">",end="")
  print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

def GetObject(cnt):
  global txid,opcode,remain_getobj_len,fd
  print("GetObject")
  print("<",end="")
  print_hex(cnt)
  _,_,opcode,txid=unpack_ptp_hdr(cnt)
  # opcode 0x1009
  p1,=struct.unpack("<L",cnt[12:16])
  print("p1=%08x" % p1)
  length=0
  if p1 in handle2path:
    fullpath=handle2path[p1]
    print(fullpath)
    fd=open(fullpath,"rb")
    filesize=fd.seek(0,2)
    fd.seek(0)
    data=fd.read(len(i0_usbd_buf)-12)
    remain_getobj_len=filesize-len(data)
    if remain_getobj_len<=0:
      remain_getobj_len=0
      fd.close()
      respond_ok()
    #print("size", filesize, "remain getobj", remain_getobj_len)
    length=PTP_CNT_INIT_LEN_DATA(i0_usbd_buf,12+filesize,PTP_USB_CONTAINER_DATA,opcode,data)
  if length==0:
    length=PTP_CNT_INIT(i0_usbd_buf,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK)
  #print(">",end="")
  #print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

def DeleteObject(cnt):
  global txid,opcode
  print("DeleteObject")
  print("<",end="")
  print_hex(cnt)
  _,_,opcode,txid=unpack_ptp_hdr(cnt)
  # opcode 0x100B
  h,=struct.unpack("<L",cnt[12:16]) # handle to delete
  p=parent(h) # parent dir where to delete
  parent_path=handle2path[p]
  #print("deleting p=",p,"h=",h)
  objname=basename(h)
  objtype=dir2handle[p][h][1]
  fullpath=handle2path[h]
  os.unlink(fullpath)
  del(dir2handle[p][h])
  del(handle2path[h])
  #print("parent path",parent_path)
  if objtype==16384: # dir
    del(path2handle[parent_path+objname+"/"])
    del(path2handle[parent_path][objname+"/"])
  else: # objtype==32768: # file
    del(path2handle[parent_path][objname])
  print("deleted",fullpath)
  length=PTP_CNT_INIT(i0_usbd_buf,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK)
  print(">",end="")
  print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

def SendObjectInfo(cnt):
  global txid,opcode,send_length,send_name,next_handle,current_send_handle
  global send_parent,send_parent_path,send_fullpath
  print("SendObjectInfo")
  print("<",end="")
  print_hex(cnt)
  _,type,opcode,txid=unpack_ptp_hdr(cnt)
  #type=unpack_type(cnt)
  #txid=unpack_txid(cnt)
  # opcode= always 0x100C
  if type==PTP_USB_CONTAINER_COMMAND: # 1
    send_parent,=struct.unpack("<L",cnt[16:20])
    if send_parent==0xffffffff:
      send_parent=0
    print("send_parent: 0x%x" % send_parent)
    send_parent_path=handle2path[send_parent]
    print("send dir path",send_parent_path)
    # prepare full buffer to read from host again
    # host will send another OUT
    usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)
  if type==PTP_USB_CONTAINER_DATA: # 2
    # we just have received data from host
    # host sends in advance file length to be sent
    send_objtype,=struct.unpack("<H",cnt[16:18])
    print("send objtype 0x%04x" % send_objtype)
    send_name=get_ucs2_string(cnt[64:])
    str_send_name=decode_ucs2_string(send_name)[:-1].decode()
    print("send name:", str_send_name)
    send_length,=struct.unpack("<L", cnt[20:24])
    print("send length:", send_length)
    send_fullpath=handle2path[send_parent]+str_send_name
    print("fullpath",send_fullpath)
    if str_send_name in path2handle[send_parent_path]:
      current_send_handle=path2handle[send_parent_path][str_send_name]
      # TODO update length after send has finished
      old_d2h=dir2handle[send_parent][current_send_handle]
      #dir2handle[send_parent][current_send_handle]=old_d2h[:-1]+(send_length,)
    else:
      next_handle+=1
      current_send_handle=next_handle
      str_send_name_p2h=str_send_name
      send_fullpath_h2p=send_fullpath
      if send_objtype==0x3001: # dir
        str_send_name_p2h+="/"
        send_fullpath_h2p+="/"
        path2handle[send_fullpath_h2p]={0:current_send_handle}
        dir2handle[current_send_handle]={}
        os.mkdir(send_fullpath)
      path2handle[send_parent_path][str_send_name_p2h]=current_send_handle
      handle2path[current_send_handle]=send_fullpath_h2p
    vfs_objtype=32768 # default is file
    if send_objtype==0x3001:
      vfs_objtype=16384 # directory
    dir2handle[send_parent][current_send_handle]=(str_send_name,vfs_objtype,0,send_length)
    print("current send handle",current_send_handle)
    # send OK response to host
    # here we must send extended "OK" response
    # with 3 addional 32-bit fields:
    # storage_id, parend_id, object_id
    length=PTP_CNT_INIT(i0_usbd_buf,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK,0x10001,send_parent,current_send_handle)
    print(">",end="")
    print_hex(i0_usbd_buf[:length])
    usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

def irq_sendobject_complete(objecthandle):
  global fd
  length=PTP_CNT_INIT(i0_usbd_buf,PTP_USB_CONTAINER_EVENT,PTP_EC_ObjectInfoChanged,objecthandle)
  print("irq>",end="")
  print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP2_IN, memoryview(i0_usbd_buf)[:length])
  fd.close()
  #ecp5.prog_close()

def SendObject(cnt):
  global txid,opcode,send_length,remaining_send_length,fd
  print("SendObject")
  print("<len(cnt)=",len(cnt),"bytes packet")
  #print("<",end="")
  #print_hex(cnt)
  _,type,opcode,txid=unpack_ptp_hdr(cnt)
  #type=unpack_type(cnt)
  #txid=unpack_txid(cnt)
  # opcode 0x100D
  if type==PTP_USB_CONTAINER_COMMAND: # 1
    #ecp5.prog_open()
    # host will send another OUT command
    # prepare full buffer to read again from host
    fd=open(send_fullpath,"wb")
    usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)
  if type==PTP_USB_CONTAINER_DATA: # 2
    # host has just sent data
    # incoming payload is 12 bytes after PTP header
    # subtract send_length by incoming payload
    if send_length>0:
      #ecp5.hwspi.write(cnt[12:])
      fd.write(cnt[12:])
      remaining_send_length=send_length-(len(cnt)-12)
      send_length=0
    print("send_length=",send_length,"remain=",remaining_send_length)

    # if host has sent all bytes it promised to send
    # report it to the host that file is complete
    if remaining_send_length<=0:
      # load interrupt response of object changed
      # first sched irq and after irq reply ok to host
      # report object 0xf1 (F1.TXT) changed
      # after irq reply OK to host
      #length=PTP_CNT_INIT(i0_usbd_buf,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK)
      #print(">",end="")
      #print_hex(i0_usbd_buf[:length])
      #usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])
      irq_sendobject_complete(current_send_handle)
    else:
      # host will send another OUT command
      # prepare full buffer to read again from host
      usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)

def CloseSession(cnt):
  print("CloseSession")
  global txid,opcode
  print("<",end="")
  print_hex(cnt)
  _,_,opcode,txid=unpack_ptp_hdr(cnt)
  #txid=unpack_txid(cnt)
  # opcode 0x1007
  length=PTP_CNT_INIT(i0_usbd_buf,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK)
  print(">",end="")
  print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

# opcodes starting from 0x1000 - callback functions
# more in libgphoto2 ptp.h and ptp.c
ptp_opcode_cb = {
  0x1000:Undefined,
  0x1001:GetDeviceInfo,
  0x1002:OpenSession,
  0x1003:CloseSession,
  0x1004:GetStorageIDs,
  # 0x1006:GetNumObjects,
  0x1005:GetStorageInfo,
  0x1007:GetObjectHandles,
  0x1008:GetObjectInfo,
  0x1009:GetObject,
  # 0x100A:GetThumb,
  0x100B:DeleteObject,
  0x100C:SendObjectInfo,
  0x100D:SendObject,
}

# EP0 control requests handlers
def handle_out(bRequest, wValue, buf):
  if bRequest == SETSTATUS and len(buf) == 6:
    status[0:6]=buf[0:6]

def handle_in(bRequest, wValue, buf):
  if bRequest == GETSTATUS and len(buf) == 6:
    buf[0:6]=status[0:6]
  return buf

# buf for control transfers
usb_buf = bytearray(64)

# USB data buffer for Bulk IN and OUT transfers.
# must be multiple of 64 bytes
i0_usbd_buf = bytearray(1024)

# not used
# on linux device works without supporting
# any of the control transfers
def _control_xfer_cb(stage, request):
  print("_control_xfer_cb", stage, bytes(request))
  bmRequestType, bRequest, wValue, wIndex, wLength = struct.unpack("<BBHHH", request)
  if stage == 1:  # SETUP
    # BUG USB_REQ_TYPE_VENDOR requests don't work
    if bmRequestType == USB_DIR_OUT | USB_REQ_TYPE_CLASS | USB_REQ_RECIP_DEVICE:
      # Data coming from host, prepare to receive it.
      return memoryview(usb_buf)[:wLength]
    elif bmRequestType == USB_DIR_IN | USB_REQ_TYPE_CLASS | USB_REQ_RECIP_DEVICE:
      # Host requests data, prepare to send it.
      buf = memoryview(usb_buf)[:wLength]
      return handle_in(bRequest, wValue, buf) # return None or buf

  elif stage == 3:  # ACK
    if bmRequestType & USB_DIR_IN:
      # EP0 TX sent.
      a=1 # process something
    else:
      # EP0 RX ready.
      buf = memoryview(usb_buf)[:wLength]
      handle_out(bRequest, wValue, buf)
  return True

# USB callback when our custom USB interface is opened by the host.
def _open_itf_cb(interface_desc_view):
  #print("_open_itf_cb", bytes(interface_desc_view))
  # Prepare to receive first data packet on the OUT endpoint.
  if interface_desc_view[11] == I0_EP1_IN:
    #print("open i0")
    usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)
  #print("_open_itf_cb", bytes(interface_desc_view))

def ep1_out_done(result, xferred_bytes):
  global remaining_send_length,fd
  if remaining_send_length>0:
    # continue receiving parts of the file
    #ecp5.hwspi.write(cnt)
    fd.write(i0_usbd_buf[:xferred_bytes])
    remaining_send_length-=xferred_bytes
    #print_hexdump(cnt)
    print("<len(cnt)=",xferred_bytes,"remaining_send_length=", remaining_send_length)
    if remaining_send_length>0:
      # host will send another OUT command
      # prepare full buffer to read again from host
      usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)
    else:
      # signal to host we have received entire file
      irq_sendobject_complete(current_send_handle)
  else:
    #length,type,code,trans_id = unpack_ptp_hdr(cnt)
    code,=struct.unpack("<H",i0_usbd_buf[6:8])
    ptp_opcode_cb[code](i0_usbd_buf[:xferred_bytes])

def ep1_in_done(result, xferred_bytes):
  global remain_getobj_len,fd
  # we have sent our data to host with IN command
  # prepare full buffer to read
  # for next host OUT command
  if length_response[0]:
    print(">",end="")
    print_hex(send_response[:length_response[0]])
    usbd.submit_xfer(I0_EP1_IN, send_response[:length_response[0]])
    length_response[0]=0 # consumed, prevent recurring
  else:
    if remain_getobj_len:
      #print("remain_getobj_len",remain_getobj_len)
      packet_len=fd.readinto(i0_usbd_buf)
      remain_getobj_len-=packet_len
      if remain_getobj_len<=0:
        remain_getobj_len=0
        fd.close()
        respond_ok() # after this send ok IN response
      #print(">",end="")
      #print_hexdump(i0_usbd_buf[:packet_len])
      usbd.submit_xfer(I0_EP1_IN, i0_usbd_buf[:packet_len])
    else:
      usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)

def ep2_in_done(result, xferred_bytes):
  # after IRQ data sent reply OK to host
  length=PTP_CNT_INIT(i0_usbd_buf,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK)
  print("after_irq>",end="")
  print_hex(i0_usbd_buf[:length])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

ep_addr_cb = {
  I0_EP1_OUT:ep1_out_done,
  I0_EP1_IN:ep1_in_done,
  I0_EP2_IN:ep2_in_done
}

def _xfer_cb(ep_addr,result,xferred_bytes):
  ep_addr_cb[ep_addr](result,xferred_bytes)

# from "/" create handle tree,
# recurse n dirs deep
# lazy browsing to save memory
# intialy do not fetch full tree
# but only the root. Browsing
# later will fetch subdirs on-demand
ls("/",0)

# Switch the USB device to our custom USB driver.
usbd = machine.USBDevice()
usbd.builtin_driver = usbd.BUILTIN_NONE
# avoid print() in *_cb functions
# if print() is neccessary do it at the
# end of _cb() function
usbd.config(
  desc_dev=_desc_dev,
  desc_cfg=_desc_cfg,
  desc_strs=_desc_strs,
  control_xfer_cb=_control_xfer_cb,
  open_itf_cb=_open_itf_cb,
  xfer_cb=_xfer_cb,
)
usbd.active(1)
