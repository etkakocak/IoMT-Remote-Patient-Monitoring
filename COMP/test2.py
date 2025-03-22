from machine import Pin, SPI
import NFC_PN532 as nfc
import time

reset_pin = Pin(9, Pin.OUT)

# SPI def
spi_dev = SPI(1,
              baudrate=1000000,
              polarity=0,
              phase=0,
              sck=Pin(10),
              mosi=Pin(11),
              miso=Pin(12))

cs_pin = Pin(13, Pin.OUT)
cs_pin.on()

# PN532 start
pn532 = nfc.PN532(spi_dev, cs_pin, reset=reset_pin)

# Firmware version
try:
    ic, ver, rev, support = pn532.get_firmware_version()
    print("PN532 found! Firmware version: {}.{}".format(ver, rev))
except RuntimeError as e:
    print("PN532 not found:", e)
    time.sleep(1)
    try:
        ic, ver, rev, support = pn532.get_firmware_version()
        print("PN532 found! Firmware version: {}.{}".format(ver, rev))
    except RuntimeError as e2:
        print("PN532 not found:", e2)

# Configure PN532 to read MiFare 
pn532.SAM_configuration()

# Scan tag loop
print("\nReady to scan...")
while True:
    uid = pn532.read_passive_target(timeout=500)  

    if uid:
        print("\nTag scanned! UID:", [hex(i) for i in uid])
        print("Tag ID: {}".format("-".join([str(i) for i in uid])))
    else:
        print(".", end="") 
    time.sleep(0.5)