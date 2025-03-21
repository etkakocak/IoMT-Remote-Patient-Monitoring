document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById("ekgChart").getContext("2d");
    let ekgChart = null;
    const ekgSelect = document.getElementById("ekg-select");
    const viewEKGBtn = document.getElementById("view-ekg-btn");

    document.getElementById("patient-select").addEventListener("change", function loadEKGHistory() {
        const uid = this.value;
        fetch(`/api/get-latest-ekg2/${uid}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.ekgResults.length > 0) {
                    ekgSelect.innerHTML = "";
                    data.ekgResults.forEach(test => {
                        const option = document.createElement("option");
                        option.value = JSON.stringify(test.ekg);
                        option.textContent = `EKG Test - ${test.date}`;
                        ekgSelect.appendChild(option);
                    });
                } else {
                    ekgSelect.innerHTML = `<option value="">No EKG history found</option>`;
                }
            })
            .catch(error => {
                console.error("❌ EKG history load error:", error);
                ekgSelect.innerHTML = `<option value="">Error loading EKG history</option>`;
            });
    });

    function updateChart(ekgData) {
            if (ekgChart) {
                ekgChart.destroy();
            }

            ekgChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array.from({ length: ekgData.length }, (_, i) => i + 1),
                    datasets: [{
                        label: "EKG Signal",
                        data: ekgData,
                        borderColor: "red",
                        borderWidth: 2,
                        fill: false,
                        pointRadius: 0,
                        tension: 0,
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            title: {
                                display: true,
                                text: "Time (ms)"
                            }
                        },
                        y: {
                            beginAtZero: false,
                            grid: {
                                color: "#ccc"
                            },
                            title: {
                                display: true,
                                text: "Voltage (mV)"
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: "black",
                                font: {
                                    size: 14
                                }
                            }
                        }
                    }
                }
            });

            document.getElementById("ekg-container").classList.remove("hidden");
        }

    viewEKGBtn.addEventListener("click", function () {
            const selectedEKG = ekgSelect.value;
            if (selectedEKG) {
                updateChart(JSON.parse(selectedEKG));
            } else {
                alert("No EKG selected!");
            }
        });

    loadEKGHistory();
});


document.getElementById("patient-select").addEventListener("change", async function fetchPatientData() {
    const uid = this.value;
    try {
        const patientResponse = await fetch(`/api/get-patient-info2/${uid}`);
        const patientData = await patientResponse.json();

        if (!patientData.success) {
            console.error("❌ Could not fetch patient info.");
            return;
        }

        const pttResponse = await fetch(`/api/get-patient-ptt2/${uid}`);
        const pttData = await pttResponse.json();

        if (!pttData.success || pttData.pttRecords.length === 0) {
            console.error("❌ No PTT data available.");
            return;
        }

        const { age, gender, smoking, exercise, hypertension, bloodpressure } = patientData.patient;
        const { a0, a1, a2 } = calculateParameters(age, gender, smoking, exercise, hypertension, bloodpressure);

        updateBPTable(pttData.pttRecords, a0, a1, a2);

    } catch (error) {
        console.error("❌ Error fetching data:", error);
    }
});

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

function calculateSBP(ptt, a0, a1, a2) {
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
