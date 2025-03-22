import time
from machine import I2C, Pin
from max30102 import MAX30102  
import spo2algorithm  

# Create I2C connection
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)

sensor = MAX30102(i2c=i2c)

INTERRUPT_PIN = Pin(6, Pin.IN, Pin.PULL_UP)


def wait_for_data():
    while INTERRUPT_PIN.value() == 1:
        time.sleep(0.001)  

# Data collection from MAX30102 FIFO.
def gather_samples(sensor, sample_count=200, sample_rate=400):
    red_list = []
    ir_list = []

    sensor.clear_fifo()  # clean FIFO

    while len(red_list) < sample_count:
        wait_for_data()  
        sensor.check()  # get new FIFO data

        while sensor.available() > 0 and len(red_list) < sample_count:
            red_list.append(sensor.get_red())
            ir_list.append(sensor.get_ir())

        time.sleep(0.005)  

    return red_list, ir_list


def adjust_led_power(sensor, red_list, ir_list):
    """
    If the signal level is too low, increase the LED current; 
    if it is too high, decrease the LED current.
    """
    avg_red = sum(red_list) / len(red_list) if len(red_list) > 0 else 0
    avg_ir = sum(ir_list) / len(ir_list) if len(ir_list) > 0 else 0

    try:
        current_led_power = ord(sensor.i2c_read_register(0x0C))  
    except:
        print("LED read error.")
        return

    if avg_red < 8000 or avg_ir < 8000 and current_led_power < 200:
        new_power = min(current_led_power + 0x10, 0xC0)  # Max 192
        sensor.set_pulse_amplitude_red(new_power)
        sensor.set_pulse_amplitude_it(new_power)
        print(f"LED power increased: {new_power}")
    
    elif avg_red > 100000 or avg_ir > 100000 and current_led_power > 80:
        new_power = max(current_led_power - 0x10, 0x50)  # Min 80
        sensor.set_pulse_amplitude_red(new_power)
        sensor.set_pulse_amplitude_it(new_power)
        print(f"LED power reduced: {new_power}")


def measure_spo2(max_attempts=5, min_valid_spo2=95):

    sensor.setup_sensor(
        led_mode=2,         
        adc_range=16384,    
        sample_rate=400,    # 400 Hz
        led_power=0xB0,     # 35 mA LED current
        sample_avg=4,       # FIFO sample
        pulse_width=411     # 411 µs
    )

    sensor.clear_fifo()

    print("SpO2 sensor started.")

    best_spo2 = 0  

    for attempt in range(1, max_attempts + 1):
        print(f"\n🔄 {attempt}. try...")

        red_list, ir_list = gather_samples(sensor, sample_count=200, sample_rate=400)

        # Dynamically adjust LED power
        adjust_led_power(sensor, red_list, ir_list)

        spo2 = spo2algorithm.process_spo2(red_list, ir_list, sample_rate=400)
        print(f"SpO2: {spo2}%")

        if spo2 > best_spo2:
            best_spo2 = spo2

        if spo2 >= min_valid_spo2:
            print(f"Found: {spo2}%")
            return spo2

        print("invalid try...")

        time.sleep(1)  

    print(f"Result: {best_spo2}%")
    return best_spo2  


if __name__ == "__main__":
    print("SpO2 started.")
    final_spo2 = measure_spo2()
    print(f"Result: {final_spo2}%")


