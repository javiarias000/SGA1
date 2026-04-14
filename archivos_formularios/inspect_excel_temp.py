import pandas as pd

def inspect_excel(file_path):
    try:
        # Read the Excel file, specifying row 4 as the header (0-indexed, so header=3)
        # and limit to columns A-H (usecols='A:H')
        df = pd.read_excel(file_path, sheet_name='GENERAL', header=3, usecols='A:H')
        print("Columns found:")
        print(df.columns.tolist())
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    excel_file = "archivos_formularios/DATOS DOCENTES 2025 Conservatorio Bolívar.xlsx"
    inspect_excel(excel_file)
