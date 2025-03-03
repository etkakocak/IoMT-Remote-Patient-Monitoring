import serial
import json
import time
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

SERIAL_PORT = "COM3"
ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)

timestamps_max = []
ir_values_max = []
peaks_max = []

timestamps_icq = []
ir_values_icq = []
peaks_icq = []

baseline_max = []
baseline_icq = []

# Kaç adet PTT bulursak final hesap yapılacak
NEEDED_PTT_COUNT = 10

# PTT sonuçlarını saklayacağımız liste
ptt_results = []

################################
# Kullanıcı Bilgileri
################################
print("=== Kullanıcı Bilgileri ===")
age = int(input("Yaşınızı girin: "))
gender = input("Cinsiyet (E/K): ").strip().upper()
gender_num = 1 if gender == "E" else 0

################################
# Seri okuma (Daha güvenli versiyon)
################################
def read_serial_data():
    try:
        line = ser.readline().decode('utf-8').strip()
        if line and line.startswith('{') and line.endswith('}'):  # JSON bütünlüğünü kontrol et
            return json.loads(line)
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print("Seri veri okuma hatası:", e)
    return None

################################
# Bant geçiren filtre
################################
def bandpass_filter(signal, fs=50.0, lowcut=0.8, highcut=2.5, order=6):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal)

################################
# Rolling window tepe tespiti
################################
WINDOW_SIZE = 200

def rolling_detect_peaks(signal_list, time_list, sensor_name, peak_list):
    """Son 2 saniye (200 örnek) veride tepe arar."""
    if len(signal_list) < WINDOW_SIZE:
        return

    window_signal = signal_list[-WINDOW_SIZE:]
    window_times = time_list[-WINDOW_SIZE:]

    filtered = bandpass_filter(
        np.array(window_signal),
        fs=50.0,
        lowcut=0.8,
        highcut=2.5,
        order=6
    )

    # Sensör bazlı eşik belirleme
    base = np.mean(filtered)
    if sensor_name == "MAX30102":
        height_th = base + 300
        prominence_th = 150
    else:
        height_th = base + 0.005  # Daha düşük eşik
        prominence_th = 0.002  # Daha düşük eşik


    peaks, _ = find_peaks(
        filtered,
        distance=50,  # En az 500 ms arası
        height=height_th,
        prominence=prominence_th
    )

    new_peaks_times = [window_times[i] for i in peaks]

    for pt in new_peaks_times:
        if pt not in peak_list:
            peak_list.append(pt)

    peak_list.sort()

################################
# PTT hesaplama
################################
def calculate_ptt(peaks1, peaks2):
    """En az 3 tepe yoksa None döner. 50-600 ms arası farkları ortalıyor."""

    if len(peaks1) < 3 or len(peaks2) < 3:
        return None

    diffs = []
    for t1 in peaks1[-3:]:  
        t2 = min(peaks2, key=lambda x: abs(x - t1))
        fark = abs(t1 - t2)

        fark = fark / 1000.0  # **Mikrosaniyeyi milisaniyeye çeviriyoruz!**

        if 50 <= fark <= 600:
            diffs.append(fark)
    
    if len(diffs) == 0:
        return None

    return np.mean(diffs)  # Ortalama PTT değeri döndür



################################
# PTT -> SBP (Tahmini Tansiyon)
################################
def estimate_sbp(ptt_ms, age, gender_num):
    ptt_s = ptt_ms / 1000.0  # PTT'yi saniyeye çeviriyoruz
    if ptt_s < 0.15:
        ptt_s = 0.15
    if ptt_s > 0.40:
        ptt_s = 0.40

    base_sbp = 50
    age_factor = 0.4 * age  # Yaş faktörünü biraz azalt
    gender_factor = 3 * gender_num  # Cinsiyet faktörünü azalt
    ptt_factor = 450 / ptt_s  # **700 yerine 450 kullan!**

    raw_sbp = base_sbp + age_factor + gender_factor + ptt_factor

    if raw_sbp < 80:
        raw_sbp = 80  # 📌 Minimum 80 mmHg olsun
    elif raw_sbp > 180:
        raw_sbp = 180  # 📌 Maksimum 180 mmHg olsun

    return raw_sbp

################################
# 1) Gürültü Ölçümü
################################
print("\n=== Gürültü Ölçümü (5sn dokunmayın) ===")
for _ in range(50):
    d = read_serial_data()
    if d:
        baseline_max.append(d["max30102_ir"])
        baseline_icq.append(d["icquanzx"])
    time.sleep(0.1)

bm = np.mean(baseline_max) if baseline_max else 0
bi = np.mean(baseline_icq) if baseline_icq else 0
print(f"Gürültü ölçümü tamamlandı. MAX30102: {bm:.2f}, ICQUANZX: {bi:.2f}")

################################
# 2) Parmak/bilek yerleştirme
################################
print("\nLütfen SOL EL BİLEĞE bir sensör, SAĞ EL PARMAĞA diğer sensör.")
time.sleep(5)
print("Ölçüm başlıyor...")

################################
# 3) Veri Toplama ve PTT Hesaplama
################################
start_time = time.time()
max_duration = 60.0
done = False

while not done:
    data = read_serial_data()
    if data:
        pico_time = data["pico_time"]

        timestamps_max.append(pico_time)
        ir_values_max.append(data["max30102_ir"])

        timestamps_icq.append(pico_time)
        ir_values_icq.append(data["icquanzx"])

        if len(ir_values_max) >= 200:
            rolling_detect_peaks(ir_values_max, timestamps_max, "MAX30102", peaks_max)
        if len(ir_values_icq) >= 200:
            rolling_detect_peaks(ir_values_icq, timestamps_icq, "ICQUANZX", peaks_icq)

        ptt_val = calculate_ptt(peaks_max, peaks_icq)
        if ptt_val:
            ptt_results.append(ptt_val)
            print(f"✓ Yeni PTT bulundu: {ptt_val:.2f} ms (toplam {len(ptt_results)})")

            if len(ptt_results) >= NEEDED_PTT_COUNT:
                done = True

    if time.time() - start_time > max_duration:
        print("\n⚠️ Süre doldu. Yeterli PTT bulunamadı.")
        break

    time.sleep(0.02)

################################
# 4) Final Hesaplama
################################
if ptt_results:
    ptt_avg = np.mean(ptt_results)
    sbp_val = estimate_sbp(ptt_avg, age, gender_num)
    print(f"\n=== Sonuçlar ===\nOrtalama PTT: {ptt_avg:.2f} ms => SBP(Tahmini): {sbp_val:.2f} mmHg")
else:
    print("PTT hesaplanamadı. Ölçüm başarısız.")

print("\nProgram sonlanıyor...")
