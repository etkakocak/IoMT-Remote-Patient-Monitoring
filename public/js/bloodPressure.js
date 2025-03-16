async function fetchPatientData() {
    try {
        // 📡 **Hastanın kişisel bilgilerini al**
        const patientResponse = await fetch('/api/get-patient-info');
        const patientData = await patientResponse.json();

        if (!patientData.success) {
            console.error("❌ Could not fetch patient info.");
            return;
        }

        // 📡 **Hastanın tüm PTT verilerini al**
        const pttResponse = await fetch('/api/get-patient-ptt');
        const pttData = await pttResponse.json();

        if (!pttData.success || pttData.pttRecords.length === 0) {
            console.error("❌ No PTT data available.");
            return;
        }

        // 🔹 **Parametreleri hesapla**
        const { age, gender, smoking, exercise, hypertension, bloodpressure } = patientData.patient;
        const { a0, a1, a2 } = calculateParameters(age, gender, smoking, exercise, hypertension, bloodpressure);

        // 📌 **PTT geçmişi tablosunu güncelle**
        updateBPTable(pttData.pttRecords, a0, a1, a2);

    } catch (error) {
        console.error("❌ Error fetching data:", error);
    }
}

// 📌 **a0, a1, a2 parametre hesaplama fonksiyonu**
function calculateParameters(age, gender, smoking, exercise, hypertension, bp_status) {
    let a0 = 105, a1 = 40, a2 = 0.005;

    if (age > 30) {
        a0 += (age - 30) * 0.2;
        a1 += (age - 30) * 1;
        a2 += (age - 30) * 0.0001;
    }

    if (gender === "Female") a0 -= 3;
    if (smoking === "Yes") { a0 += 5; a1 += 5; }
    if (exercise === "Yes") { a0 -= 5; a1 -= 5; }
    if (hypertension === "Yes") { a0 += 10; a1 += 10; a2 += 0.001; }
    if (bp_status === "Low") { a0 -= 10; }
    if (bp_status === "High") { a0 += 10; }

    return { a0, a1, a2 };
}

// 📌 **SBP hesaplama fonksiyonu**
function calculateSBP(ptt, a0, a1, a2) {
    // return Math.round(a0 + Math.sqrt(a1 + (a2 / (ptt ** 2))));
    const sbp = a0 + a1 * Math.exp(-a2 * ptt);
    return sbp.toFixed(2);
}

// 📌 **Tansiyon geçmişi tablosunu güncelleme fonksiyonu**
function updateBPTable(pttRecords, a0, a1, a2) {
    const tableBody = document.querySelector("#bp-history-table tbody");
    tableBody.innerHTML = ""; // Önce tabloyu temizle

    pttRecords.forEach(record => {
        const sbp = calculateSBP(record.PTT, a0, a1, a2); // 🔥 Her PTT için ayrı hesaplama
        const formattedDate = new Date(record.createdAt).toLocaleString(); // 🔥 Doğru tarih formatı

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${formattedDate}</td>
            <td>${sbp} mmHg</td>
        `;
        tableBody.appendChild(row);
    });
}


// **Sayfa yüklendiğinde çalıştır**
document.addEventListener("DOMContentLoaded", fetchPatientData);
