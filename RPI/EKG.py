import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import json

ser = serial.Serial('COM3', 115200, timeout=1)

# Veri saklamak için liste
data = [0] * 100  # Son 100 veriyi saklayacağız

def update(frame):
    global data
    line = ser.readline().decode().strip()  
    if line:  
        print(f"Pico'dan Gelen Veri: {line}")  
    try:
        value = json.loads(line)  # JSON formatındaki değeri al
        if isinstance(value, int):  # Eğer gelen veri sayısal ise ekle
            data.append(value)
            data = data[-100:]  # Son 100 değeri tut
        else:
            print(f"Geçersiz Veri Formatı: {line}")
    except json.JSONDecodeError:
        print(f"HATALI JSON FORMAT: {line}")  

    ax.clear()
    ax.plot(data, color='red')
    ax.set_ylim(0, 65535)  # ADC maksimum değeri
    ax.set_title("Gerçek Zamanlı Nabız Sensörü")
    ax.set_ylabel("ADC Değeri")
    ax.set_xlabel("Zaman")

# Matplotlib animasyonu başlat
fig, ax = plt.subplots()
ani = animation.FuncAnimation(fig, update, interval=50)
plt.show()
