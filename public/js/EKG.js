document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById("ekgChart").getContext("2d");
    let ekgChart = null;
    const ekgSelect = document.getElementById("ekg-select");
    const viewEKGBtn = document.getElementById("view-ekg-btn");

    function loadEKGHistory() {
        fetch('/api/get-latest-ekg')
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
                console.error("EKG history load error:", error);
                ekgSelect.innerHTML = `<option value="">Error loading EKG history</option>`;
            });
    }

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
