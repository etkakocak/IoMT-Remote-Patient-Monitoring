from machine import Pin, SPI
import NFC_PN532 as nfc
import time
import urequests  # HTTP istekleri için MicroPython kütüphanesi
import network

# WiFi Bilgileri (Burayı kendi ağınıza göre değiştirin!)
WIFI_SSID = "ssid"
WIFI_PASSWORD = "password"

# Web Sunucusunun URL'si
SERVER_URL = "http://192.168.x.x:5000/api/send-tag"

# SPI Tanımlama
spi_dev = SPI(1,
              baudrate=1000000,
              polarity=0,
              phase=0,
              sck=Pin(10),
              mosi=Pin(11),
              miso=Pin(12))

cs_pin = Pin(13, Pin.OUT)
cs_pin.on()

# 📡 WiFi'ye Bağlan
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    print("🔄 WiFi'ye bağlanıyor...")
    while not wlan.isconnected():
        time.sleep(1)

    print("✅ WiFi'ye bağlandı! IP Adresi:", wlan.ifconfig()[0])

connect_wifi()

# PN532 Başlat
pn532 = nfc.PN532(spi_dev, cs_pin)

# Firmware Versiyonu Kontrolü
try:
    ic, ver, rev, support = pn532.get_firmware_version()
    print("✅ PN532 bulundu! Firmware sürümü: {}.{}".format(ver, rev))
except RuntimeError as e:
    print("❌ PN532 algılanamadı:", e)
    time.sleep(1)
    try:
        ic, ver, rev, support = pn532.get_firmware_version()
        print("✅ PN532 bulundu! Firmware sürümü: {}.{}".format(ver, rev))
    except RuntimeError as e2:
        print("❌ İkinci denemede de algılanamadı:", e2)

# MiFare kartları okuyabilmek için PN532'yi konfigüre et
pn532.SAM_configuration()

# Kart okuma döngüsü
print("\n📡 Kart okutmaya hazır! Bir kartı modüle yaklaştır...")

while True:
    uid = pn532.read_passive_target(timeout=500)  # 500 ms boyunca kart tarama

    if uid:
        uid_str = "-".join([str(i) for i in uid])
        print("\n📍 Kart Algılandı! UID:", uid_str)
        # Web Sunucusuna POST isteği gönder
        try:
            response = urequests.post(SERVER_URL, json={"uid": uid_str})
            print("📡 Sunucudan gelen cevap:", response.text)
            response.close()
        except Exception as e:
            print("❌ Sunucuya bağlanırken hata:", e)
    else:
        print(".", end="")  # Kart yoksa ekrana nokta koyarak beklediğini göster

    time.sleep(0.5)

