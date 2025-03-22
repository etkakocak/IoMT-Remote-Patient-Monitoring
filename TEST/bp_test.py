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

NEEDED_PTT_COUNT = 10

ptt_results = []

print("Patient info")
age = int(input("Yaşınızı girin: "))
gender = input("Cinsiyet (E/K): ").strip().upper()
gender_num = 1 if gender == "E" else 0
smoking = input("Sigara içiyor musunuz? (E/H): ").strip().upper() == "E"
exercise = input("Haftada en az 3 gün düzenli spor yapıyor musunuz? (E/H): ").strip().upper() == "E"
hypertension = input("Daha önce hipertansiyon veya diyabet tanısı aldınız mı? (E/H): ").strip().upper() == "E"
bp_status = input("Tansiyonunuz genellikle nasıl? (Yüksek/Y, Düşük/D, Normal/N): ").strip().upper()

def estimate_parameters(age, gender, smoking, exercise, hypertension, bp_status):

    # Test values
    a0 = 52.6  
    a1 = 4900  
    a2 = 10  

    if age > 30:
        a0 = a0 + (age - 30) * 0.25  
        a1 = a1 + (age - 30) * 80  
        a2 = a2 + (age - 30) * 0.2  

    if gender == "K":
        a0 -= 3  

    if smoking:
        a1 *= 1.10
        a2 *= 1.10

    if exercise:
        a1 *= 0.95  
        a2 *= 0.95  

    if hypertension:
        a0 += 7
        a1 *= 1.15
        a2 *= 1.15

    if bp_status == "D":
        a0 -= 5  
        a1 *= 0.90  
        a2 *= 0.90  

    if bp_status == "Y":
        a0 += 10  
        a1 *= 1.20  
        a2 *= 1.20  

    return a0, a1, a2

a0, a1, a2 = estimate_parameters(age, gender, smoking, exercise, hypertension, bp_status)

# Serial read
def read_serial_data():
    try:
        line = ser.readline().decode('utf-8').strip()
        if line and line.startswith('{') and line.endswith('}'):  
            return json.loads(line)
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print("Seri veri okuma hatası:", e)
    return None

def bandpass_filter(signal, fs=50.0, lowcut=0.8, highcut=2.5, order=6):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal)

WINDOW_SIZE = 200

def rolling_detect_peaks(signal_list, time_list, sensor_name, peak_list):
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

    base = np.mean(filtered)
    if sensor_name == "MAX30102":
        height_th = base + 300
        prominence_th = 150
    else:
        height_th = base + 0.005  
        prominence_th = 0.002  

    peaks, _ = find_peaks(
        filtered,
        distance=50,  
        height=height_th,
        prominence=prominence_th
    )

    new_peaks_times = [window_times[i] for i in peaks]

    for pt in new_peaks_times:
        if pt not in peak_list:
            peak_list.append(pt)

    peak_list.sort()

# PTT test calc
def calculate_ptt(peaks1, peaks2):
    if len(peaks1) < 3 or len(peaks2) < 3:
        return None

    diffs = []
    for t1 in peaks1[-3:]:  
        t2 = min(peaks2, key=lambda x: abs(x - t1))
        fark = abs(t1 - t2)

        fark = fark / 1000.0  

        if 50 <= fark <= 600:
            diffs.append(fark)
    
    if len(diffs) == 0:
        return None

    return np.mean(diffs)  

# SBP test calc
def estimate_sbp(ptt_ms, a0, a1, a2):
    ptt_s = ptt_ms / 1000.0  
    sbp = a0 + np.sqrt(a1 + (a2 / (ptt_s ** 2)))

    return sbp

# Sensor Noise Measurement
print("Gürültü Ölçümü")
for _ in range(50):
    d = read_serial_data()
    if d:
        baseline_max.append(d["max30102_ir"])
        baseline_icq.append(d["icquanzx"])
    time.sleep(0.1)

bm = np.mean(baseline_max) if baseline_max else 0
bi = np.mean(baseline_icq) if baseline_icq else 0
print(f"Gürültü ölçümü tamamlandı. MAX30102: {bm:.2f}, ICQUANZX: {bi:.2f}")

print("\nThe left hand finger is one sensor, the right hand finger is the other sensor.")
time.sleep(5)
print("Calc starts...")

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
            print(f"PTT found: {ptt_val:.2f} ms (len {len(ptt_results)})")

            if len(ptt_results) >= NEEDED_PTT_COUNT:
                done = True

    if time.time() - start_time > max_duration:
        print("Not enough PTT was found.")
        break

# Final calc test
if ptt_results:
    ptt_avg = np.mean(ptt_results)
    sbp_val = estimate_sbp(ptt_avg, a0, a1, a2)
    print(f"\n Result \nPTT: {ptt_avg:.2f} SBP(appr): {sbp_val:.2f} mmHg")
else:
    print("PTT calculation failed.")

print("\nProgram exits...")
