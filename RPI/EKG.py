import machine
import time
import ujson

adc = machine.ADC(26)  # ADC pin
WINDOW_SIZE = 200  
INIT_IGNORE_TIME = 10  # ignore time bandpass filter

def measure_ekg():
    print("EKG starts.")
    
    start_time = time.time()

    while time.time() - start_time < INIT_IGNORE_TIME:
        adc.read_u16()  
        time.sleep(0.05)  

    print("EKG starts...")

    ekg_data = []

    while len(ekg_data) < WINDOW_SIZE:
        value = adc.read_u16()  
        ekg_data.append(value)
        time.sleep(0.05)  

    print("EKG done.")
    return ekg_data  
