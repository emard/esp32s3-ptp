import os
import machine
import sys
sys.path.extend(['/lib'])

# this is useful for testing but not necessary
# once everything is working
#uart = machine.UART(0,115200,tx=16,rx=17)
#os.dupterm(uart)

# from shared/tinyusb/tusb_config.h
#    USBD_STR_MANUF (0x01)
#    USBD_STR_PRODUCT (0x02)
#    USBD_STR_SERIAL (0x03)
# from shared/tinyusb/mp_usbd_descriptor.c
#   .iManufacturer = USBD_STR_MANUF,
#   .iProduct = USBD_STR_PRODUCT,
#   .iSerialNumber = USBD_STR_SERIAL,

# string indices in the default descriptor
i_str_manuf = 0x01
i_str_product = 0x02
i_str_serial = 0x03

# module ID (will be read from DIP switches)
module_id = 0x11

# make strings
str_module_id = f'{module_id:02x}'
str_unique_id = f'{int.from_bytes(machine.unique_id()):x}'
str_serial = f'{str_unique_id}_{str_module_id}'
str_product = f'proto_meter_{module_id:02x}'
str_manuf = 'TheStumbler'

mystrings = {}
mystrings[0] = None # need this for language
mystrings[i_str_manuf] = str_manuf
mystrings[i_str_product] = str_product
mystrings[i_str_serial] = str_serial

#for s in mystrings.items(): print(s)

usbdev = machine.USBDevice()
desc_dev = usbdev.BUILTIN_DEFAULT.desc_dev
desc_cfg = usbdev.BUILTIN_DEFAULT.desc_cfg
usbdev.active(False)
usbdev.builtin_driver = usbdev.BUILTIN_DEFAULT
usbdev.config( 
    desc_dev, desc_cfg, \
    desc_strs=mystrings \
)
usbdev.active(True)
