import network
import urequests
import time
from machine import Pin, SPI
import NFC_PN532 as nfc
import bodytemp
import spo2
import EKG
import bp_live

# 📡 **WiFi Bilgileri**
WIFI_SSID = "Etkas S24 Ultra"
WIFI_PASSWORD = "etka12345"

# 📡 **Web Sunucusunun IP Adresi**
SERVER_IP = "192.168.3.181"

SCAN_CARD_URL = f"http://{SERVER_IP}:5000/api/scan-card"
SEND_TAG_URL = f"http://{SERVER_IP}:5000/api/send-tag"

MEASURE_BODYTEMP_URL = f"http://{SERVER_IP}:5000/api/measure-bodytemp"
STORE_BODYTEMP_URL = f"http://{SERVER_IP}:5000/api/store-bodytemp"

SPO2_URL = f"http://{SERVER_IP}:5000/api/spo2"
STORE_SPO2_URL = f"http://{SERVER_IP}:5000/api/store-spo2"

EKG_URL = f"http://{SERVER_IP}:5000/api/EKG"
STORE_EKG_URL = f"http://{SERVER_IP}:5000/api/store-EKG"

BP_URL = f"http://{SERVER_IP}:5000/api/BP"
STORE_BP_URL = f"http://{SERVER_IP}:5000/api/store-BP"

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
        scanresponse = urequests.get(SCAN_CARD_URL)
        measresponse = urequests.get(MEASURE_BODYTEMP_URL)
        spo2response = urequests.get(SPO2_URL)
        ekgresponse = urequests.get(EKG_URL)
        bpresponse = urequests.get(BP_URL)
        
        scandata = scanresponse.json()
        measdata = measresponse.json()
        spo2data = spo2response.json()
        ekgdata = ekgresponse.json()
        bpdata = bpresponse.json()
        
        scanresponse.close()
        measresponse.close()
        spo2response.close()
        ekgresponse.close()
        bpresponse.close()
        
        if scandata == ('SCAN'):
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
                
        if measdata == ('measure'):
            print("🔄 Web Sunucusu Vücut Sıcaklığı Ölçümünü Başlattı!")
            temp = bodytemp.get_bodytemp()  # ✅ Vücut sıcaklığını ölç
            if temp:
                # 📡 **Sunucuya sıcaklık verisini gönder**
                print(f"📡 Sunucuya sıcaklık {temp:.2f}°C gönderiliyor...")
                response = urequests.post(STORE_BODYTEMP_URL, json={"temperature": temp})
                print("📡 Sunucudan gelen cevap:", response.text)
                response.close()
            else:
                print("❌ Sıcaklık sensörü bulunamadı!")
            print("⏳ Test tamamlandı.")
            time.sleep(10)
        
        if spo2data == ('spo2start'):
            print("Web Sunucusu spo2 Ölçümünü Başlattı!")
            spo2_dat = spo2.measure_spo2()  
            if spo2_dat:
                # 📡 **Sunucuya sıcaklık verisini gönder**
                print(f"📡 Sunucuya {spo2_dat:.2f} gönderiliyor...")
                response = urequests.post(STORE_SPO2_URL, json={"spo2": spo2_dat})
                print("📡 Sunucudan gelen cevap:", response.text)
                response.close()
            else:
                print("❌ sensör bulunamadı!")
            print("⏳ Test tamamlandı.")
            time.sleep(10)
        
        if ekgdata == ('EKGstart'):
            print("Web Sunucusu EKG Ölçümünü Başlattı!")
            EKG_dat = EKG.measure_ekg()  
            if EKG_dat:
                # 📡 **Sunucuya sıcaklık verisini gönder**
                print(f"📡 Sunucuya gönderiliyor...")
                response = urequests.post(STORE_EKG_URL, json={"EKG": EKG_dat})
                print("📡 Sunucudan gelen cevap:", response.text)
                response.close()
            else:
                print("❌ sensör bulunamadı!")
            print("⏳ Test tamamlandı.")
            time.sleep(10)
        
        if bpdata == ('BPstart'):
            print("Web Sunucusu BP Ölçümünü Başlattı!")
            bp_live.start_bp_measurement()  # ✅ **BP Ölçümünü Başlat**
            print("⏳ Test tamamlandı.")
            time.sleep(10)

    except Exception as e:
        print("❌ Hata:", e)

    time.sleep(1)  # 1 saniye bekle ve tekrar kontrol et

