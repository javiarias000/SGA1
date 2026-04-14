
import pandas as pd

# Ruta al archivo Excel
file_path = 'archivos_formularios/DATOS DOCENTES 2025 Conservatorio Bolívar.xlsx'

# Leer la fila 4 (índice 3) para obtener los encabezados
try:
    headers_df = pd.read_excel(file_path, header=3, nrows=0)
    headers = headers_df.columns.tolist()

    # Imprimir los encabezados de la A a la H
    print("Encabezados encontrados en la fila 4 (Columnas A-H):")
    for header in headers[0:8]:
        print(f"- {header}")

except Exception as e:
    print(f"Error al leer el archivo: {e}")
