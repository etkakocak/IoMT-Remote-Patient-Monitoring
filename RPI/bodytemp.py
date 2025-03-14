import machine
import onewire
import ds18x20
import time

# 📡 DS18B20 Sensör Bağlantısı
ds_pin = machine.Pin(28)  
ow = onewire.OneWire(ds_pin)
ds = ds18x20.DS18X20(ow)

roms = ds.scan()  # Sensörleri tarıyoruz
if not roms:
    print("❌ Vücut sıcaklığı sensörü bulunamadı!")
else:
    print(f"✅ {len(roms)} DS18B20 sensörü bulundu.")

# 🔥 **Vücut Sıcaklığı Ölçüm Fonksiyonu**
def get_bodytemp():
    if not roms:
        return None  # Sensör yoksa None döndür

    print("\n⏳ 40 saniye boyunca ölçüm yapılıyor... Sensörü vücudunuza yerleştirin!")
    
    timeout = time.time() + 40  # 40 saniyelik süre başlat
    last_temp = None  # Son ölçülen sıcaklık değeri
    
    while time.time() < timeout:
        ds.convert_temp()  # Ölçüm başlat
        time.sleep_ms(750)  # DS18B20 ölçüm süresi
        for rom in roms:
            temp = ds.read_temp(rom)
            last_temp = temp  # En son ölçülen sıcaklık güncellenir
            print(f"🌡️ Güncel Vücut Sıcaklığı: {temp:.2f}°C")
        time.sleep(2)  # 2 saniye bekleyerek tekrar ölç

    print(f"\n✅ Ölçüm tamamlandı! Son vücut sıcaklığı: {last_temp:.2f}°C")
    return last_temp  # 40 saniye sonunda en son ölçülen sıcaklığı döndür

