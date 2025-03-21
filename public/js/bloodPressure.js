async function fetchPatientData() {
    try {
        // get patient info
        const patientResponse = await fetch('/api/get-patient-info');
        const patientData = await patientResponse.json();

        if (!patientData.success) {
            console.error("Could not fetch patient info.");
            return;
        }

        // get PTT values
        const pttResponse = await fetch('/api/get-patient-ptt');
        const pttData = await pttResponse.json();

        if (!pttData.success || pttData.pttRecords.length === 0) {
            console.error("No PTT data available.");
            return;
        }

        const { age, gender, smoking, exercise, hypertension, bloodpressure } = patientData.patient;
        const { a0, a1, a2 } = calculateParameters(age, gender, smoking, exercise, hypertension, bloodpressure);

        updateBPTable(pttData.pttRecords, a0, a1, a2);

    } catch (error) {
        console.error("Error fetching data:", error);
    }
}

// calculate a0, a1, a2 parameters used in SBP algorithm
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

// Systolic Blood Pressure algorithm
function calculateSBP(ptt, a0, a1, a2) {
    // return Math.round(a0 + Math.sqrt(a1 + (a2 / (ptt ** 2))));
    const sbp = a0 + a1 * Math.exp(-a2 * ptt);
    return sbp.toFixed(2);
}

function updateBPTable(pttRecords, a0, a1, a2) {
    const tableBody = document.querySelector("#bp-history-table tbody");
    tableBody.innerHTML = ""; 

    pttRecords.forEach(record => {
        const sbp = calculateSBP(record.PTT, a0, a1, a2); 
        const formattedDate = new Date(record.createdAt).toLocaleString(); 

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${formattedDate}</td>
            <td>${sbp} mmHg</td>
        `;
        tableBody.appendChild(row);
    });
}

document.addEventListener("DOMContentLoaded", fetchPatientData);
