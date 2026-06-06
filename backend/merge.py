import pandas as pd
import glob

print("Buscando y uniendo las 8 partes del dataset...")


archivos_csv = sorted(glob.glob('backend/Datos_Limpios_ChocoRoles_parte_*.csv'))

df_completo = pd.concat((pd.read_csv(archivo) for archivo in archivos_csv), ignore_index=True)

print(f"¡Reconstrucción exitosa! Total de filas listas para usar: {len(df_completo)}")

