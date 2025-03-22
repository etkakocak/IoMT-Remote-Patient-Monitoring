import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import json

ser = serial.Serial('COM3', 115200, timeout=1)

data = [0] * 100  # List for last 100 data

def update(frame):
    global data
    line = ser.readline().decode().strip()  
    if line:  
        print(f"From pico: {line}")  
    try:
        value = json.loads(line)  # get value at JSON format
        if isinstance(value, int):  
            data.append(value)
            data = data[-100:]  
        else:
            print(f"Invalid Data Format: {line}")
    except json.JSONDecodeError:
        print(f"INCORRECT JSON FORMAT: {line}")  

    ax.clear()
    ax.plot(data, color='red')
    ax.set_ylim(0, 65535)  # ADC
    ax.set_title("EKG")
    ax.set_ylabel("ADC")
    ax.set_xlabel("Time")

# Matplotlib animation
fig, ax = plt.subplots()
ani = animation.FuncAnimation(fig, update, interval=50)
plt.show()
