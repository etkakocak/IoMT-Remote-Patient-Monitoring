import machine
import time
import ujson

adc = machine.ADC(26)  
uart = machine.UART(0, baudrate=115200) 

buffer = []  # Hareketli ortalama için veri saklama listesi
window_size = 5  # Kaç örneğin ortalamasını alacağımızı belirler

while True:
    value = adc.read_u16()  
    buffer.append(value)

    if len(buffer) > window_size:
        buffer.pop(0)  # Eski verileri çıkartarak pencereyi sabit tut

    avg_value = sum(buffer) // len(buffer)  # Hareketli ortalama hesapla

    json_data = ujson.dumps(avg_value)  # JSON formatına çevir
    uart.write(json_data + "\n")  # Seri porttan gönder
    print(json_data)  

    time.sleep(0.1)  

