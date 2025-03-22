import math

def moving_average(signal, window_size=5):
    filtered_signal = []
    for i in range(len(signal) - window_size + 1):
        window = signal[i:i + window_size]
        filtered_signal.append(sum(window) / window_size)
    return filtered_signal

def mean(values):
    return sum(values) / len(values)

def standard_deviation(values):
    avg = mean(values)
    variance = sum((x - avg) ** 2 for x in values) / len(values)
    return variance ** 0.5


# spo2 calc with PPG data
def process_spo2(red_list, ir_list, sample_rate=400):

    # DC component tracking with IIR filter
    alpha = 0.05  
    red_baseline = red_list[0] if len(red_list) > 0 else 0
    ir_baseline  = ir_list[0] if len(ir_list) > 0 else 0

    red_ac_list = []
    ir_ac_list  = []

    for i in range(len(red_list)):
        red_val = red_list[i]
        ir_val  = ir_list[i]

        # IIR update
        red_baseline = alpha * red_val + (1 - alpha) * red_baseline
        ir_baseline  = alpha * ir_val  + (1 - alpha) * ir_baseline

        # AC signal calc
        red_ac_list.append(red_val - red_baseline)
        ir_ac_list.append(ir_val - ir_baseline)

    red_ac = max(red_ac_list) - min(red_ac_list)
    ir_ac  = max(ir_ac_list)  - min(ir_ac_list)

    tail_len = 10
    if len(red_list) < tail_len or len(ir_list) < tail_len:
        return 0

    red_dc = mean(red_list[-tail_len:])
    ir_dc  = mean(ir_list[-tail_len:])

    ratio = ((red_ac / red_dc) / (ir_ac / ir_dc)) if ir_dc != 0 and red_dc != 0 else 0

    spo2 = 110 - 25 * ratio

    if spo2 > 100:
        spo2 = 100
    elif spo2 < 70:
        spo2 = 70

    return round(spo2, 1)
