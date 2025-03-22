import machine
import onewire
import ds18x20
import time

# DS18B20 sensor onewire connect
ds_pin = machine.Pin(28)  
ow = onewire.OneWire(ds_pin)
ds = ds18x20.DS18X20(ow)

roms = ds.scan()  # sensor roms
if not roms:
    print("No sensor found.")
else:
    print(f"✅ {len(roms)} DS18B20 found.")

def get_bodytemp():
    if not roms:
        return None  

    print("\n40 second measurement.")
    
    timeout = time.time() + 40  
    last_temp = None  
    
    while time.time() < timeout:
        ds.convert_temp()  
        time.sleep_ms(750)  
        for rom in roms:
            temp = ds.read_temp(rom)
            last_temp = temp  
            print(f"Calculating: {temp:.2f}°C")
        time.sleep(2)  

    print(f"\nDone. Bodytemp: {last_temp:.2f}°C")
    return last_temp  

