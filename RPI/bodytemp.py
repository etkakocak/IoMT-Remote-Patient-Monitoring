import machine
import onewire
import ds18x20
import time

ds_pin = machine.Pin(28)  
ow = onewire.OneWire(ds_pin)
ds = ds18x20.DS18X20(ow)

roms = ds.scan()
print("ROM IDs:", roms)

if not roms:
    print("No sensor found!")
else:
    print(f"{len(roms)} DS18B20 found.")
    while True:
        ds.convert_temp()
        time.sleep_ms(750)
        for rom in roms:
            temp = ds.read_temp(rom)
            print(f"Body Temperature: {temp:.2f}°C")
        time.sleep(2)

