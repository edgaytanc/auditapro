document.addEventListener("DOMContentLoaded", function () {
  const dataElement = document.getElementById(
    "financialDashboardData"
  );

  if (!dataElement || typeof Chart === "undefined") {
    return;
  }

  let dashboardData;

  try {
    dashboardData = JSON.parse(
      dataElement.textContent
    );
  } catch (error) {
    console.error(
      "No fue posible leer los datos del Dashboard:",
      error
    );

    return;
  }

  Chart.defaults.font.family =
    'Inter, "Segoe UI", sans-serif';

  Chart.defaults.color = "#64748b";

  const gridColor = "rgba(226, 232, 240, 0.75)";

  const baseTooltip = {
    backgroundColor: "#0f172a",
    titleColor: "#ffffff",
    bodyColor: "#e2e8f0",
    padding: 10,
    cornerRadius: 8,
    displayColors: true
  };

  const trendCanvas = document.getElementById(
    "financialTrendChart"
  );

  if (trendCanvas) {
    new Chart(trendCanvas, {
      type: "line",

      data: {
        labels: dashboardData.trend.labels,

        datasets: [
          {
            label: "Iniciadas",
            data: dashboardData.trend.started,
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59, 130, 246, 0.11)",
            pointBackgroundColor: "#3b82f6",
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 5,
            borderWidth: 2,
            tension: 0.35,
            fill: true
          },
          {
            label: "Completadas",
            data: dashboardData.trend.completed,
            borderColor: "#22c55e",
            backgroundColor: "rgba(34, 197, 94, 0.08)",
            pointBackgroundColor: "#22c55e",
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 5,
            borderWidth: 2,
            tension: 0.35,
            fill: true
          }
        ]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,

        interaction: {
          mode: "index",
          intersect: false
        },

        plugins: {
          tooltip: baseTooltip,

          legend: {
            position: "top",
            align: "end",

            labels: {
              usePointStyle: true,
              pointStyle: "circle",
              boxWidth: 7,
              boxHeight: 7,
              padding: 14,
              font: {
                size: 9,
                weight: "600"
              }
            }
          }
        },

        scales: {
          x: {
            grid: {
              display: false
            },

            border: {
              display: false
            },

            ticks: {
              font: {
                size: 9
              }
            }
          },

          y: {
            beginAtZero: true,

            suggestedMax: 5,

            grid: {
              color: gridColor
            },

            border: {
              display: false
            },

            ticks: {
              precision: 0,
              stepSize: 1,
              font: {
                size: 9
              }
            }
          }
        }
      }
    });
  }

  function createDoughnutChart(
    canvasId,
    chartData
  ) {
    const canvas = document.getElementById(canvasId);

    if (!canvas) {
      return;
    }

    new Chart(canvas, {
      type: "doughnut",

      data: {
        labels: chartData.labels,

        datasets: [
          {
            data: chartData.values,
            backgroundColor: chartData.colors,
            borderWidth: 0,
            hoverOffset: 5
          }
        ]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "66%",

        plugins: {
          legend: {
            display: false
          },

          tooltip: baseTooltip
        }
      }
    });
  }

  createDoughnutChart(
    "financialStatusChart",
    dashboardData.status
  );

  createDoughnutChart(
    "financialTypeChart",
    dashboardData.types
  );

  const performanceCanvas = document.getElementById(
    "financialPerformanceChart"
  );

  if (performanceCanvas) {
    new Chart(performanceCanvas, {
      type: "bar",

      data: {
        labels: dashboardData.performance.labels,

        datasets: [
          {
            label: "Horas ejecutadas",
            data: dashboardData.performance.values,
            backgroundColor: "#3b82f6",
            hoverBackgroundColor: "#2563eb",
            borderRadius: 7,
            borderSkipped: false,
            maxBarThickness: 46
          }
        ]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,

        plugins: {
          legend: {
            display: false
          },

          tooltip: {
            ...baseTooltip,

            callbacks: {
              label: function (context) {
                return context.parsed.y + " horas";
              }
            }
          }
        },

        scales: {
          x: {
            grid: {
              display: false
            },

            border: {
              display: false
            },

            ticks: {
              font: {
                size: 9
              }
            }
          },

          y: {
            beginAtZero: true,

            grid: {
              color: gridColor
            },

            border: {
              display: false
            },

            ticks: {
              font: {
                size: 9
              },

              callback: function (value) {
                return value + " h";
              }
            }
          }
        }
      }
    });
  }
});