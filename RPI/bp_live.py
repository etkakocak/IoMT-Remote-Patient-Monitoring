import time
import ujson
import urequests
from machine import I2C, Pin, ADC
from max30102 import MAX30102

# **Server Adresi**
SERVER_URL = "http://192.168.3.181:5000/api/live-bp"

# **MAX30102 Sensörü Ayarları**
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
sensor1 = MAX30102(i2c=i2c)

# **ICQUANZX ADC Bağlantısı (Örn: GPIO26)**
sensor2 = ADC(Pin(26))

# **Sensörü Başlatma Fonksiyonu**
def initialize_sensors():
    print("🔄 MAX30102 başlatılıyor...")
    sensor1.setup_sensor()
    time.sleep(1)

    if not sensor1.check_part_id():
        print("❌ HATA: MAX30102 sensörü bulunamadı! Lütfen bağlantıları kontrol edin.")
        return False

    print("✅ MAX30102 başarıyla başlatıldı!")
    return True

# **Sensörden Veri Okuma**
def read_sensor_data():
    """Sensörlerden veri oku ve gönder."""
    try:
        ir = sensor1.get_ir() or 0
        red = sensor1.get_red() or 0
        ir2_raw = sensor2.read_u16()
        ir2 = ir2_raw / 65535  # Normalize edilmiş değer
        timestamp = time.ticks_ms()  # Milisaniye bazlı zaman damgası

        return {
            "timestamp": timestamp,
            "max30102_ir": ir,
            "max30102_red": red,
            "icquanzx": ir2
        }
    except Exception as e:
        print("❌ Sensör okuma hatası:", e)
        return None

# **Ana Çalışma Fonksiyonu (Main.py'den çağrılacak)**
def start_bp_measurement():
    if not initialize_sensors():
        return False  # Sensör başlatılamadıysa çık

    print("⏳ BP Ölçümü Başlıyor! Sunucuya veri akışı başlatıldı...")

    try:
        for _ in range(200):
            sensor_data = read_sensor_data()

            if sensor_data:
                try:
                    response = urequests.post(SERVER_URL, json=sensor_data)
                    print(f"📡 Veri gönderildi: {sensor_data}")
                    response.close()
                except Exception as e:
                    print("❌ Veri gönderme hatası:", e)

            time.sleep(0.02)  # **50 Hz veri akışı**
    
    except KeyboardInterrupt:
        print("🔴 BP Ölçümü durduruldu!")
        return False  # Döngü durdurulduğunda False döndür
