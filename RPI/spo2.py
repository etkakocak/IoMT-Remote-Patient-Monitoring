# main.py

import time
from machine import I2C, Pin
from max30102 import MAX30102  
import spo2algorithm  

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)

sensor = MAX30102(i2c=i2c)

# INT pini tanımlama
INTERRUPT_PIN = Pin(6, Pin.IN, Pin.PULL_UP)


def wait_for_data():
    """ INT pini aktif olana kadar bekle, gereksiz `check()` çağrılarından kaçın. """
    while INTERRUPT_PIN.value() == 1:
        time.sleep(0.001)  


def gather_samples(sensor, sample_count=200, sample_rate=400):
    """
    MAX30102 FIFO'dan hızlı veri toplama.
    """
    red_list = []
    ir_list = []

    sensor.clear_fifo()  # FIFO'yu temizle

    while len(red_list) < sample_count:
        wait_for_data()  # Sensör veri hazır olana kadar bekle
        sensor.check()  # FIFO'daki yeni verileri al

        while sensor.available() > 0 and len(red_list) < sample_count:
            red_list.append(sensor.get_red())
            ir_list.append(sensor.get_ir())

        time.sleep(0.005)  

    return red_list, ir_list


def adjust_led_power(sensor, red_list, ir_list):
    """
    Eğer sinyal seviyesi çok düşükse LED akımını artır,
    çok yüksekse LED akımını azalt.
    """
    avg_red = sum(red_list) / len(red_list) if len(red_list) > 0 else 0
    avg_ir = sum(ir_list) / len(ir_list) if len(ir_list) > 0 else 0

    # Geçerli LED gücünü oku
    try:
        current_led_power = ord(sensor.i2c_read_register(0x0C))  # IR LED gücünü oku
    except:
        print("LED gücü okunamadı!")
        return

    # 🔥 LED gücü gereksiz yere sürekli artırılmasın
    if avg_red < 8000 or avg_ir < 8000 and current_led_power < 200:
        new_power = min(current_led_power + 0x10, 0xC0)  # Maks 192
        sensor.set_pulse_amplitude_red(new_power)
        sensor.set_pulse_amplitude_it(new_power)
        print(f"LED gücü artırıldı: {new_power}")
    
    elif avg_red > 100000 or avg_ir > 100000 and current_led_power > 80:
        new_power = max(current_led_power - 0x10, 0x50)  # Min 80
        sensor.set_pulse_amplitude_red(new_power)
        sensor.set_pulse_amplitude_it(new_power)
        print(f"LED gücü düşürüldü: {new_power}")


# Sensör kurulum
sensor.setup_sensor(
    led_mode=2,         # 2 => sadece Kırmızı + IR ölçer
    adc_range=16384,    # 16-bit ADC aralığı
    sample_rate=400,    # 400 Hz
    led_power=0xB0,     # 35 mA LED akımı
    sample_avg=4,       # FIFO içinde 4'lü ortalama
    pulse_width=411     # 411 µs
)

# FIFO'yu temizle
sensor.clear_fifo()

print("MAX30102 başlatıldı.")
print("Lütfen 5 saniye içinde parmağınızı sensöre yerleştirin...")

for i in range(5, 0, -1):
    print(i)
    time.sleep(1)

print("SpO₂ ölçüm döngüsü başlıyor...")

while True:
    print("\nVeri toplanıyor (yaklaşık 5 saniye)...")
    
    red_list, ir_list = gather_samples(sensor, sample_count=200, sample_rate=400)

    # LED gücünü dinamik ayarla
    adjust_led_power(sensor, red_list, ir_list)
        
    spo2 = spo2algorithm.process_spo2(red_list, ir_list, sample_rate=400)

    print(f"SpO₂: {spo2}%")

    time.sleep(0.1)

