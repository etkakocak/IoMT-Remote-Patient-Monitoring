import network
import urequests
import time
from machine import Pin, SPI
import NFC_PN532 as nfc

# 📡 **WiFi Bilgileri**
WIFI_SSID = "ssid"
WIFI_PASSWORD = "password"

# 📡 **Web Sunucusunun IP Adresi**
SERVER_IP = "192.168.x.x"
SCAN_CARD_URL = f"http://{SERVER_IP}:5000/api/scan-card"
SEND_TAG_URL = f"http://{SERVER_IP}:5000/api/send-tag"

# 📡 **WiFi'ye Bağlan**
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    print("🔄 WiFi'ye bağlanıyor...")
    while not wlan.isconnected():
        time.sleep(1)

    print("✅ WiFi'ye bağlandı! IP Adresi:", wlan.ifconfig()[0])

connect_wifi()

# 🔄 **Kart Okuma Fonksiyonu**
def scan_card():
    print("\n📡 Kart okutmaya başlıyoruz...")

    timeout = time.time() + 3  # 5 saniye bekleme süresi
    while time.time() < timeout:
        uid = pn532.read_passive_target(timeout=500)

        if uid:
            uid_str = "-".join([str(i) for i in uid])
            print(f"📍 Kart Algılandı! UID: {uid_str}")
            return uid_str  # Okunan UID'yi döndür

    print("❌ Kart okunamadı, zaman aşımı!")
    return None  # Zaman aşımı durumunda None döndür

# 📡 **SPI & PN532 Başlat**
spi_dev = SPI(1, baudrate=1000000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
cs_pin = Pin(13, Pin.OUT)
cs_pin.on()

pn532 = nfc.PN532(spi_dev, cs_pin)

try:
    ic, ver, rev, support = pn532.get_firmware_version()
    print("✅ PN532 bulundu! Firmware sürümü: {}.{}".format(ver, rev))
except RuntimeError as e:
    print("❌ PN532 algılanamadı:", e)

pn532.SAM_configuration()

# 📡 **RPi Tarafında Sürekli Bekleme Döngüsü**
while True:
    try:
        response = urequests.get(SCAN_CARD_URL)
        data = response.json()
        response.close()

        if data == ('SCAN'):
            print("🔄 Web Sunucusu Tarama Başlattı!")
            # ✅ **Kart taramasını başlat**
            uid = scan_card()  
            if uid:
                # 📡 **Sunucuya tag bilgisini gönder**
                print(f"📡 Sunucuya UID {uid} gönderiliyor...")
                response = urequests.post(SEND_TAG_URL, json={"uid": uid})
                print("📡 Sunucudan gelen cevap:", response.text)
                response.close()
            else:
                print("❌ Kart taranamadı veya zaman aşımı!")

    except Exception as e:
        print("❌ Hata:", e)

    time.sleep(1)  # 1 saniye bekle ve tekrar kontrol et
