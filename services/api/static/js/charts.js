// Gráfico de Promedios (uso genérico)
function crearGraficoPromedios(elementId, datos) {
  const el = document.getElementById(elementId);
  if (!el || !window.Chart) return;
  const ctx = el.getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: datos.nombres || [],
      datasets: [{
        label: 'Promedio',
        data: datos.promedios || [],
        backgroundColor: datos.colores || '#3B82F6',
        borderRadius: 8,
      }]
    },
    options: {
      responsive: true,
      scales: { y: { beginAtZero: true, max: 10 } }
    }
  });
}

// Auto-inicialización opcional si existe window.CHART_DATA
if (typeof window !== 'undefined' && window.CHART_DATA) {
  document.addEventListener('DOMContentLoaded', function() {
    crearGraficoPromedios('graficoPromedios', window.CHART_DATA);
  });
}

// Exportar a global por compatibilidad
window.crearGraficoPromedios = crearGraficoPromedios;
