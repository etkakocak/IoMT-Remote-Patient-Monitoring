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
smoking = input("Sigara içiyor musunuz? (E/H): ").strip().upper() == "E"
exercise = input("Haftada en az 3 gün düzenli spor yapıyor musunuz? (E/H): ").strip().upper() == "E"
hypertension = input("Daha önce hipertansiyon veya diyabet tanısı aldınız mı? (E/H): ").strip().upper() == "E"
bp_status = input("Tansiyonunuz genellikle nasıl? (Yüksek/Y, Düşük/D, Normal/N): ").strip().upper()

################################
# Dinamik a0, a1, a2 Hesaplama
################################
################################
# Bilimsel a0, a1, a2 Hesaplama
################################
def estimate_parameters(age, gender, smoking, exercise, hypertension, bp_status):
    """
    Kullanıcının yaşı, cinsiyeti, sigara kullanımı, spor alışkanlığı, hipertansiyon geçmişi ve
    tansiyon durumuna göre a0, a1 ve a2 parametrelerini hesaplar.
    """

    # 🔹 Arteriyel Elastisite (a0) Hesaplama
    a0 = 2.0 - (age / 100)  # Yaş arttıkça arteriyel elastisite azalır
    if gender == "K":
        a0 += 0.1  # Kadınlarda genç yaşta biraz daha yüksek olabilir
    if smoking:
        a0 -= 0.2  # Sigara içmek arteriyel elastisiteyi düşürür
    if exercise:
        a0 += 0.2  # Düzenli spor yapmak elastisiteyi artırır
    if hypertension:
        a0 -= 0.3  # Hipertansiyon arterlerin sertleşmesine neden olur

    # 🔹 Arteriyel Sertlik (a1) Hesaplama (PWV yaşa bağlı artıyor)
    a1 = 5.0 + 0.1 * (age - 20)  # 20 yaş için 5.0 m/s, her yıl için 0.1 ekleniyor

    # 🔹 Nabız Dalgası Yayılma Hızı (a2) Hesaplama
    a2 = 0.5  # Baz değer
    if hypertension:
        a2 += 1.0  # Hipertansiyon arteriyel sertliği artırır
    if smoking:
        a2 += 0.5  # Sigara arter duvarlarını sertleştirir
    if bp_status == "D":
        a2 -= 0.5  # Düşük tansiyonu olanlarda PWV daha düşük olur
    if bp_status == "Y":
        a2 += 0.5  # Yüksek tansiyonu olanlarda PWV artar

    return a0, a1, a2

# Kullanıcıya özel parametreleri belirle
a0, a1, a2 = estimate_parameters(age, gender, smoking, exercise, hypertension, bp_status)

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
# PTT -> SBP (Bilimsel Model)
################################
def estimate_sbp(ptt_ms, a0, a1, a2):
    ptt_s = ptt_ms / 1000.0  # PTT'yi saniyeye çeviriyoruz
    sbp = a0 + np.sqrt(a1 + (a2 / (ptt_s ** 2)))

    # return max(80, min(sbp, 180))  # 📌 SBP değerini 80-180 mmHg arasında sınırla
    return sbp

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

################################
# 4) Final Hesaplama
################################
if ptt_results:
    ptt_avg = np.mean(ptt_results)
    sbp_val = estimate_sbp(ptt_avg, a0, a1, a2)
    print(f"\n=== Sonuçlar ===\nOrtalama PTT: {ptt_avg:.2f} ms => SBP(Tahmini): {sbp_val:.2f} mmHg")
else:
    print("PTT hesaplanamadı. Ölçüm başarısız.")

print("\nProgram sonlanıyor...")
