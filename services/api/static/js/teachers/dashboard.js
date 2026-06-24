let aporteCounter = 1;

document.getElementById('addAporte').addEventListener('click', function() {
    aporteCounter++;
    const container = document.getElementById('aportesContainer');
    const newRow = document.createElement('div');
    newRow.className = 'grid grid-cols-12 gap-2 aporte-row';
    newRow.innerHTML = `
        <div class="col-span-5"><input type="text" name="aporte_nombre_${aporteCounter}" class="block w-full rounded-md border-gray-300 shadow-sm" placeholder="Nombre del aporte"></div>
        <div class="col-span-3"><input type="number" name="aporte_nota_${aporteCounter}" class="calificacion-input block w-full rounded-md border-gray-300 shadow-sm" min="0" max="10" step="0.01" placeholder="Nota"></div>
        <div class="col-span-3"><input type="text" name="obs_${aporteCounter}" class="block w-full rounded-md border-gray-300 shadow-sm text-sm" placeholder="Observación"></div>
        <div class="col-span-1"><button type="button" class="remove-aporte w-full h-full bg-red-500 text-white rounded-md hover:bg-red-600"><i class="fas fa-trash"></i></button></div>
    `;
    container.appendChild(newRow);
    newRow.querySelector('.remove-aporte').addEventListener('click', () => {
        newRow.remove();
        updateRemoveButtons();
        calcularPromedioTiempoReal();
    });
    newRow.querySelector('.calificacion-input').addEventListener('input', calcularPromedioTiempoReal);
    updateRemoveButtons();
});

function updateRemoveButtons() {
    const rows = document.querySelectorAll('.aporte-row');
    rows.forEach((row, index) => {
        const btn = row.querySelector('.remove-aporte');
        btn.disabled = rows.length === 1;
    });
}

function calcularPromedioTiempoReal() {
    const inputs = document.querySelectorAll('.calificacion-input');
    let suma = 0, count = 0;
    inputs.forEach(input => {
        const valor = parseFloat(input.value);
        if (!isNaN(valor) && valor > 0) {
            suma += valor;
            count++;
        }
    });
    const promedio = count > 0 ? (suma / count).toFixed(2) : '0.00';
    document.getElementById('promedioValor').textContent = promedio;
    document.getElementById('promedioPreview').style.display = count > 0 ? 'block' : 'none';
}

document.querySelectorAll('.calificacion-input').forEach(i => i.addEventListener('input', calcularPromedioTiempoReal));

function limpiarFormulario() {
    document.getElementById('formCalificaciones').reset();
    document.getElementById('promedioPreview').style.display = 'none';
    const container = document.getElementById('aportesContainer');
    const rows = container.querySelectorAll('.aporte-row');
    rows.forEach((row, index) => { if (index > 0) row.remove(); });
    aporteCounter = 1;
    updateRemoveButtons();
}
