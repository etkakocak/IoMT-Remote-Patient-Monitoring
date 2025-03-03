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
gender_num = 1 if gender=="E" else 0

################################
# Seri okuma
################################
def read_serial_data():
    try:
        line = ser.readline().decode('utf-8').strip()
        if line:
            return json.loads(line)
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print("Seri veri okuma hatası:", e)
    return None

################################
# Bant geçiren filtre
################################
def bandpass_filter(signal, fs=100.0, lowcut=0.8, highcut=2.5, order=6):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal)

################################
# Rolling window tepe tespiti
################################
WINDOW_SIZE = 300

def rolling_detect_peaks(
    signal_list,
    time_list,
    sensor_name,
    peak_list
):
    """Son 3 saniye (300 örnek) veride tepe arar."""
    if len(signal_list) < WINDOW_SIZE:
        return

    window_signal = signal_list[-WINDOW_SIZE:]
    window_times = time_list[-WINDOW_SIZE:]

    filtered = bandpass_filter(
        np.array(window_signal),
        fs=100.0,
        lowcut=0.8,
        highcut=2.5,
        order=6
    )

    # Sıkı parametre
    base = np.mean(filtered)
    if sensor_name=="MAX30102":
        height_th = base + 500
        prominence_th = 200
    else:
        height_th = base + 2000
        prominence_th = 500

    # distance=100 => en az 1 sn arası
    peaks, _ = find_peaks(
        filtered,
        distance=100,
        height=height_th,
        prominence=prominence_th
    )

    new_peaks_times = [window_times[i] for i in peaks]

    added=0
    for pt in new_peaks_times:
        if pt not in peak_list:
            peak_list.append(pt)
            added += 1

    peak_list.sort()
    if added>0:
        print(f"📌 {sensor_name} için {len(peak_list)} tepe noktası (yeni {added}): {peak_list[-5:]}")

################################
# PTT hesaplama
################################
def calculate_ptt(peaks1, peaks2):
    """En az 3 tepe yoksa None döner. 50-600 ms arası farkları ortalıyor."""
    if len(peaks1)<50 or len(peaks2)<50:
        return None
    recent1 = peaks1[-5:]
    recent2 = peaks2[-5:]
    diffs=[]
    for t1 in recent1:
        t2 = min(recent2, key=lambda x: abs(x-t1))
        fark = abs(t1 - t2)
        if 50<=fark<=600:
            diffs.append(fark)
    if len(diffs)==0:
        return None
    return np.mean(diffs)

################################
# Ters PTT -> SBP (Saturasyon)
################################
def estimate_sbp(ptt_ms, age, gender_num):
    ptt_s = ptt_ms/1000.0
    # 0.2-0.35 aralığına kıstır
    if ptt_s<0.2:
        ptt_s=0.2
    if ptt_s>0.35:
        ptt_s=0.35

    base_sbp=50
    age_factor=0.5*age
    gender_factor=5*gender_num
    ptt_factor=700/ptt_s

    raw_sbp = base_sbp + age_factor + gender_factor + ptt_factor
    if raw_sbp<60:
        raw_sbp=60
    elif raw_sbp>200:
        raw_sbp=200
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
print("Gürültü ölçümü tamamlandı.")
print(f"MAX30102 baseline ort.: {bm:.2f}")
print(f"ICQUANZX baseline ort.: {bi:.2f}")

################################
# 2) Parmak/bilek yerleştirme (5sn)
################################
print("\nLütfen SOL EL BİLEĞE bir sensör, SAĞ EL PARMAĞA diğer sensör.")
time.sleep(5)
print("Ölçüm başlıyor...")

################################
# 3) Veri Toplama + Birden Çok PTT Bulma
################################
start_time = time.time()
max_duration=60.0

ptt_results = []
done=False

while True:
    data = read_serial_data()
    if data:
        timestamps_max.append(data["time"])
        ir_values_max.append(data["max30102_ir"])

        timestamps_icq.append(data["time"])
        ir_values_icq.append(data["icquanzx"])

        # rolling detect
        if len(ir_values_max)>=300:
            rolling_detect_peaks(ir_values_max, timestamps_max, "MAX30102", peaks_max)
        if len(ir_values_icq)>=300:
            rolling_detect_peaks(ir_values_icq, timestamps_icq, "ICQUANZX", peaks_icq)

        # PTT hesaplayıp diziye at
        ptt_val = calculate_ptt(peaks_max, peaks_icq)
        if ptt_val is not None:
            # Bir ptt bulduk
            ptt_results.append(ptt_val)
            print(f"✓ Yeni PTT bulundu: {ptt_val:.2f} ms (toplam {len(ptt_results)})")

            # Yeterli sayıda PTT bulundu mu?
            if len(ptt_results)>=NEEDED_PTT_COUNT:
                done=True
                break

    # Süre kontrol
    elapsed=time.time()-start_time
    if elapsed>max_duration:
        print("\n⚠️ Süre doldu. Yeterli PTT bulunamadı veya <3 PTT var.")
        break

    time.sleep(0.01)

################################
# 4) Final Hesaplama
################################
if len(ptt_results)==0:
    print("Hiç PTT bulunamadı. Ölçüm başarısız.")
elif not done:
    # En az 1 PTT var ama needed_count dolmadı, yine de ortalama yapabiliriz
    print(f"\nYeterli ({NEEDED_PTT_COUNT}) PTT yok ama {len(ptt_results)} adet bulduk.")
    ptt_avg = np.mean(ptt_results)
    sbp_val = estimate_sbp(ptt_avg, age, gender_num)
    print(f"Ortalama PTT: {ptt_avg:.2f} ms => SBP(tahmin): {sbp_val:.2f} mmHg")
else:
    # needed_count e ulaştık
    ptt_avg = np.mean(ptt_results)
    sbp_val = estimate_sbp(ptt_avg, age, gender_num)
    print("\n=== Sonuçlar ===")
    print(f"{len(ptt_results)} adet PTT bulundu: {ptt_results}")
    print(f"Ortalama PTT: {ptt_avg:.2f} ms => SBP(tahmin): {sbp_val:.2f} mmHg")

print("\nProgram sonlanıyor...")
