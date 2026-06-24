import pandas as pd
import os
from pathlib import Path

def excel_to_csv():
    print("\n" + "="*50)
    print("📋 CONVERTIDOR DE EXCEL A CSV POR HOJA")
    print("="*50)
    
    ruta_trabajo = input("Ingrese la ruta de la carpeta con archivos Excel: ").strip()
    if not os.path.exists(ruta_trabajo):
        print(f"❌ La ruta '{ruta_trabajo}' no existe")
        return
    
    # Intenta encontrar el archivo de matriculados
    archivo_excel = None
    archivos = [f for f in os.listdir(ruta_trabajo) if f.endswith(('.xlsx', '.xls'))]
    
    # Busca el archivo que contiene 'Matriculados' en el nombre
    for f in archivos:
        if 'Matriculados' in f or 'matriculados' in f:
            archivo_excel = f
            break
            
    if not archivo_excel:
        print("❌ No se encontró ningún archivo de 'Matriculados' en la carpeta.")
        return

    ruta_completa = os.path.join(ruta_trabajo, archivo_excel)
    ruta_salida_csv = Path('./output_csv')
    ruta_salida_csv.mkdir(exist_ok=True)

    print(f"\n✅ Archivo encontrado: {archivo_excel}")
    print(f"👉 Convirtiendo hojas a CSV en la carpeta '{ruta_salida_csv}'...")

    try:
        xls = pd.ExcelFile(ruta_completa, engine='openpyxl')
        
        for sheet_name in xls.sheet_names:
            try:
                df = pd.read_excel(ruta_completa, sheet_name=sheet_name, engine='openpyxl')
                
                # Definir el nombre del archivo CSV
                nombre_csv = f"{archivo_excel.replace('.xlsx', '').replace('.xls', '')}_{sheet_name}.csv"
                ruta_csv = ruta_salida_csv / nombre_csv
                
                # Exportar usando el separador de punto y coma (;)
                df.to_csv(ruta_csv, index=False, sep=';', encoding='utf-8-sig')
                print(f"  [OK] Exportada hoja '{sheet_name}' a: {ruta_csv}")
                
            except Exception as e:
                print(f"  [ERROR] Falló la exportación de la hoja '{sheet_name}': {e}")
                
        print("\n✅ Proceso de conversión finalizado. Revise la carpeta 'output_csv'.")

    except Exception as e:
        print(f"❌ Error al abrir el archivo Excel: {e}")

if __name__ == "__main__":
    excel_to_csv()