import sys
import json
import numpy as np
from scipy.signal import find_peaks

try:
    sys.stdout.reconfigure(encoding='utf-8')

    # Read incoming data
    input_data = sys.stdin.read()
    sensor_data = json.loads(input_data)

    if len(sensor_data) < 10:
        print(json.dumps({"success": False, "error": "Not enough data"}))
        sys.exit(0)

    timestamps = np.array([d["timestamp"] for d in sensor_data])
    ir_values = np.array([d["max30102_ir"] for d in sensor_data])
    icq_values = np.array([d["icquanzx"] for d in sensor_data])

    # Statistics of sensor data
    ir_std = np.std(ir_values)
    icq_std = np.std(icq_values)

    # If the variance is too low, it is difficult to find the peak
    if ir_std < 0.5 or icq_std < 0.0001:
        print(json.dumps({"success": False, "error": "Sensor data too flat, no peaks detected"}))
        sys.exit(0)

    # Detect first peaks
    peaks_ir, _ = find_peaks(ir_values, distance=15, prominence=0.5)
    peaks_icq, _ = find_peaks(icq_values, distance=20, prominence=0.0001)

    if len(peaks_ir) < 3:
        peaks_ir, _ = find_peaks(ir_values, distance=10, prominence=0.2)

    if len(peaks_icq) < 3:
        peaks_icq, _ = find_peaks(icq_values, distance=15, prominence=0.00005)

    if len(peaks_ir) < 3 or len(peaks_icq) < 3:
        print(json.dumps({"success": False, "error": "Not enough peaks"}))
        sys.exit(0)

    # PTT calc
    ptt_values = []
    for t1 in peaks_ir[-3:]:
        t2 = min(peaks_icq, key=lambda x: abs(x - t1))
        diff = abs(timestamps[t1] - timestamps[t2])

        if 100 <= diff <= 1500:  
            ptt_values.append(diff)

    if not ptt_values:
        print(json.dumps({"success": False, "error": "PTT Calculation Failed"}))
        sys.exit(0)

    avg_ptt = np.mean(ptt_values)

    # JSON output
    print(json.dumps({"success": True, "PTT": avg_ptt}))

except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
    sys.exit(0)
