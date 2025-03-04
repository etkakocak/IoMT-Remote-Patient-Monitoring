from machine import Pin, SPI
import NFC_PN532 as nfc
import time

# Donanımsal RESET pini
reset_pin = Pin(9, Pin.OUT)

# SPI tanımlama
spi_dev = SPI(1,
              baudrate=1000000,
              polarity=0,
              phase=0,
              sck=Pin(10),
              mosi=Pin(11),
              miso=Pin(12))

cs_pin = Pin(13, Pin.OUT)
cs_pin.on()

# PN532 başlat
pn532 = nfc.PN532(spi_dev, cs_pin, reset=reset_pin)

# Firmware versiyonu kontrolü
try:
    ic, ver, rev, support = pn532.get_firmware_version()
    print("PN532 bulundu! Firmware sürümü: {}.{}".format(ver, rev))
except RuntimeError as e:
    print("PN532 algılanamadı:", e)
    time.sleep(1)
    try:
        ic, ver, rev, support = pn532.get_firmware_version()
        print("PN532 bulundu! Firmware sürümü: {}.{}".format(ver, rev))
    except RuntimeError as e2:
        print("İkinci denemede de algılanamadı:", e2)

# MiFare kartları okuyabilmek için PN532'yi konfigüre et
pn532.SAM_configuration()

# Kart okuma döngüsü
print("\nKart okutmaya hazır! Bir kartı modüle yaklaştır...")
while True:
    uid = pn532.read_passive_target(timeout=500)  # 500 ms boyunca kart tarama

    if uid:
        print("\nKart Algılandı! UID:", [hex(i) for i in uid])
        print("Kart ID: {}".format("-".join([str(i) for i in uid])))
    else:
        print(".", end="")  # Kart yoksa ekrana nokta koyarak beklediğini göster
    time.sleep(0.5)

