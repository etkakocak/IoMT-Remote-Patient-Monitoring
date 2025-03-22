import network
import urequests
import time
from machine import Pin, SPI
import NFC_PN532 as nfc
import bodytemp
import spo2
import EKG
import bp_live

WIFI_SSID = "SSID"
WIFI_PASSWORD = "PASSWORD"

# Web server IP
SERVER_IP = "192.168.3.181"

# Web server APIs
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

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    print("Connecting to WiFi...")
    while not wlan.isconnected():
        time.sleep(1)

    print("Connected to WiFi. IP Address:", wlan.ifconfig()[0])

connect_wifi()

# Scan tag/card by PN532
def scan_card():
    print("\nScanning...")

    timeout = time.time() + 3  
    while time.time() < timeout:
        uid = pn532.read_passive_target(timeout=500)

        if uid:
            uid_str = "-".join([str(i) for i in uid])
            print(f"Tag detected, UID: {uid_str}")
            return uid_str  

    print("scan timeout")
    return None  

# SPI & PN532 start
spi_dev = SPI(1, baudrate=1000000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
cs_pin = Pin(13, Pin.OUT)
cs_pin.on()

pn532 = nfc.PN532(spi_dev, cs_pin)

try:
    ic, ver, rev, support = pn532.get_firmware_version()
    print("PN532 found! Firmware version: {}.{}".format(ver, rev))
except RuntimeError as e:
    print("PN532 cannot found:", e)

pn532.SAM_configuration()

# Rpi listen server requests loop
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
            print("Server started scanning.")
            uid = scan_card()  
            if uid:
                print(f"UID {uid} is sent to server...")
                response = urequests.post(SEND_TAG_URL, json={"uid": uid})
                print("Response from server:", response.text)
                response.close()
            else:
                print("Scan timeout!")
                
        if measdata == ('measure'):
            print("Server started Body Temperature measurement.")
            temp = bodytemp.get_bodytemp()  
            if temp:
                print(f"Bodytemp {temp:.2f}°C is sent to server...")
                response = urequests.post(STORE_BODYTEMP_URL, json={"temperature": temp})
                print("Response from server:", response.text)
                response.close()
            else:
                print("Sensor not found.")
            print("Test done.")
            time.sleep(10)
        
        if spo2data == ('spo2start'):
            print("Server started spo2 measurement.")
            spo2_dat = spo2.measure_spo2()  
            if spo2_dat:
                print(f"Spo2 {spo2_dat:.2f} is sent to server...")
                response = urequests.post(STORE_SPO2_URL, json={"spo2": spo2_dat})
                print("Response from server:", response.text)
                response.close()
            else:
                print("Sensor not found.")
            print("Test done.")
            time.sleep(10)
        
        if ekgdata == ('EKGstart'):
            print("Server started EKG measurement.")
            EKG_dat = EKG.measure_ekg()  
            if EKG_dat:
                print(f"Sent to server...")
                response = urequests.post(STORE_EKG_URL, json={"EKG": EKG_dat})
                print("Response from server:", response.text)
                response.close()
            else:
                print("Sensor not found.")
            print("Test done.")
            time.sleep(10)
        
        if bpdata == ('BPstart'):
            print("Server started BP measurement.")
            bp_live.start_bp_measurement()  
            print("Test done.")
            time.sleep(10)

    except Exception as e:
        print("Error:", e)

    time.sleep(1) 

