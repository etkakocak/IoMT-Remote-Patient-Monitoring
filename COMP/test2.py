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