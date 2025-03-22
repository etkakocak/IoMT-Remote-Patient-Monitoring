import time
import ujson
import urequests
from machine import I2C, Pin, ADC
from max30102 import MAX30102

# API
SERVER_URL = "http://192.168.3.181:5000/api/live-bp"

# MAX30102
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
sensor1 = MAX30102(i2c=i2c)

# ICQUANZX
sensor2 = ADC(Pin(26))

def initialize_sensors():
    print("MAX30102 starts...")
    sensor1.setup_sensor()
    time.sleep(1)

    if not sensor1.check_part_id():
        print("Error")
        return False

    print("MAX30102 started.")
    return True

def read_sensor_data():
    try:
        ir = sensor1.get_ir() or 0
        red = sensor1.get_red() or 0
        ir2_raw = sensor2.read_u16()
        ir2 = ir2_raw / 65535  # Normalized value
        timestamp = time.ticks_ms()  # Millisecond based timestamp

        return {
            "timestamp": timestamp,
            "max30102_ir": ir,
            "max30102_red": red,
            "icquanzx": ir2
        }
    except Exception as e:
        print("Error:", e)
        return None

def start_bp_measurement():
    if not initialize_sensors():
        return False  

    print("BP Measurement Starts, Data flow to server started...")

    try:
        for _ in range(200):
            sensor_data = read_sensor_data()

            if sensor_data:
                try:
                    response = urequests.post(SERVER_URL, json=sensor_data)
                    print(f"Data sent: {sensor_data}")
                    response.close()
                except Exception as e:
                    print("Error sending:", e)

            time.sleep(0.02)  # 50 Hz
    
    except KeyboardInterrupt:
        print("BP Measurement Stopped.")
        return False  
