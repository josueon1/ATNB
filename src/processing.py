import pandas as pd

def load_data():
    data_frame = pd.read_csv('/data/acidentes2023.csv', sep=';', encoding='latin-1')
    
    #padronizar as colunas
    data_frame.columns = data_frame.columns.str.strip().str.lower().str.replace(' ', '_')
    
    #remoção de campos nulos
    data_frame = data_frame.dropna(subset=['uf', 'causa_acidente', 'horario'])
    
    # criar coluna de hora
    data_frame["hora"] = pd.to_datetime(data_frame["horario"], format='%H:%M').dt.hour
    
    return data_frame

def acidentes_por_estado(data_frame):
    return data_frame.groupby('uf').size().sort_values(ascending=False)

def acidentes_por_causa(data_frame):
    return data_frame.groupby('causa_acidente').size().sort_values(ascending=False).head(10)

def acidentes_por_hora(data_frame):
    return data_frame.groupby('hora').size().sort_values()