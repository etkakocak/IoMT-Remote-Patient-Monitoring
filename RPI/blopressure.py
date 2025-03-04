import time
import ujson  # JSON formatında veri göndermek için
from machine import I2C, Pin, ADC, UART
from max30102 import MAX30102

# **UART Ayarları (PC ile Seri Haberleşme)**
uart = UART(0, baudrate=115200)

# **MAX30102 I2C Bağlantısı**
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
sensor1 = MAX30102(i2c=i2c)  # MAX30102 Sensörü

# **ICQUANZX ADC Bağlantısı (Örn: GPIO26)**
sensor2 = ADC(Pin(26))  # Analog giriş pini

# **Sensörü başlat ve kontrol et**
print("MAX30102 başlatılıyor...")
sensor1.setup_sensor()  # Sensörü başlat
time.sleep(1)  # Başlatma için kısa bir gecikme

# **Sensör çalışıyor mu kontrol edelim**
if not sensor1.check_part_id():
    print("HATA: MAX30102 sensörü bulunamadı! Lütfen bağlantıları kontrol edin.")
    while True:
        time.sleep(1)  # Sensör yoksa programı durdur

print("MAX30102 başarıyla başlatıldı!")

def read_sensor_data():
    """Sensörlerden IR verisini oku ve zaman damgasıyla döndür."""
    try:
        # **MAX30102'dan IR ve RED değerlerini oku**
        ir = sensor1.get_ir()
        red = sensor1.get_red()

        # **Eğer sensör hatalı değer döndürürse 0 yap**
        if ir is None:
            ir = 0
        if red is None:
            red = 0

        # **ICQUANZX ADC'den veri oku ve normalize et (0 - 1)**
        ir2_raw = sensor2.read_u16()
        ir2 = ir2_raw / 65535  # Normalize edilmiş değer

        # **Zaman damgası (mikro saniye hassasiyetinde)**
        pico_timestamp = time.ticks_us()
        pc_timestamp = time.time() * 1000  # Milisaniye formatında (PC için referans)
        
        return pico_timestamp, pc_timestamp, ir, red, ir2
    except Exception as e:
        print("Sensör okuma hatası:", e)
        return None, None, 0, 0, 0  # Hata varsa sıfır değerler döndür

# **Sürekli veri gönderme döngüsü**
while True:
    pico_time, pc_time, ir1, red1, ir2 = read_sensor_data()

    if pico_time is not None and pc_time is not None:
        # **JSON formatında terminalde göster**
        data = {
            "pico_time": pico_time,   # Mikro saniye hassasiyetinde zaman damgası
            "pc_time": pc_time,       # Milisaniye bazlı PC referans zamanı
            "max30102_ir": ir1,
            "max30102_red": red1,
            "icquanzx": ir2           # Normalleştirilmiş ADC verisi
        }

        json_data = ujson.dumps(data)  # **JSON formatına çevir**

        # **Buffer taşmasını önlemek için UART temizleme**
        uart.write(json_data + "\n")
        uart.flush()  # Buffer içeriğini hemen gönder

        print(json_data)  # **Terminalde göster**

    time.sleep(0.02)  # **Önceden 10ms idi, şimdi 20ms yaparak veri stabilitesini artırdık**

