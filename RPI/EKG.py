import machine
import time
import ujson

adc = machine.ADC(26)  # ADC pini (EKG sensörünün bağlı olduğu pin)
WINDOW_SIZE = 200  # 200 veri toplanacak
INIT_IGNORE_TIME = 10  # İlk 10 saniyeyi göz ardı et

def measure_ekg():
    """
    EKG verisini ölçer.
    - İlk 10 saniye gelen verileri **umursamaz**.
    - Sonrasında **200 adet** veri toplar.
    - **JSON formatında bir liste döndürür.**
    """

    print("⏳ EKG başlatılıyor... İlk 10 saniye veriler yok sayılacak.")
    
    start_time = time.time()

    while time.time() - start_time < INIT_IGNORE_TIME:
        adc.read_u16()  # İlk 10 saniyedeki verileri sadece oku, kaydetme
        time.sleep(0.05)  

    print("✅ EKG ölçümü başlıyor! 200 veri toplanacak...")

    ekg_data = []

    while len(ekg_data) < WINDOW_SIZE:
        value = adc.read_u16()  # ADC değerini oku
        ekg_data.append(value)
        time.sleep(0.05)  # Örnekleme süresi (20 Hz ≈ 0.05s per sample)

    print("✅ EKG ölçümü tamamlandı.")
    return ekg_data  # Listeyi döndür
