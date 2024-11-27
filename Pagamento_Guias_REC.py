import streamlit as st
import pandas as pd
import mysql.connector
import decimal
from babel.numbers import format_currency
from google.oauth2 import service_account
import gspread 

def gerar_df_phoenix(vw_name, base_luck):

    # Parametros de Login AWS
    config = {
    'user': 'user_automation_jpa',
    'password': 'luck_jpa_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': base_luck
    }
    # Conexão as Views
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()

    request_name = f'SELECT * FROM {vw_name}'

    # Script MySql para requests
    cursor.execute(
        request_name
    )
    # Coloca o request em uma variavel
    resultado = cursor.fetchall()
    # Busca apenas o cabecalhos do Banco
    cabecalho = [desc[0] for desc in cursor.description]

    # Fecha a conexão
    cursor.close()
    conexao.close()

    # Coloca em um dataframe e muda o tipo de decimal para float
    df = pd.DataFrame(resultado, columns=cabecalho)
    df = df.applymap(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)
    return df

def puxar_dados_phoenix():

    st.session_state.df_escalas = gerar_df_phoenix('vw_payment_guide', 'test_phoenix_recife')

    st.session_state.df_escalas = st.session_state.df_escalas[~(st.session_state.df_escalas['Status da Reserva'].isin(['CANCELADO', 'PENDENCIA DE IMPORTAÇÃO'])) & 
                                                              ~(pd.isna(st.session_state.df_escalas['Status da Reserva'])) & ~(pd.isna(st.session_state.df_escalas['Escala'])) & 
                                                              ~(pd.isna(st.session_state.df_escalas['Guia']))].reset_index(drop=True)

def puxar_tarifarios():

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE')
    
    sheet = spreadsheet.worksheet('Tarifário Robô')

    sheet_data = sheet.get_all_values()

    st.session_state.df_tarifario = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

    st.session_state.df_tarifario['Valor'] = pd.to_numeric(st.session_state.df_tarifario['Valor'], errors='coerce')

    st.session_state.df_tarifario['Valor Idioma'] = pd.to_numeric(st.session_state.df_tarifario['Valor Idioma'], errors='coerce')

def avaliar_observacao(observacoes):

    return 50 if 'barco_carneiros' in observacoes else 0

def avaliar_idioma(idiomas):

    return 'X' if any(idioma != 'pt-br' for idioma in idiomas) else ''

def verificar_tarifarios(df_escalas_group, id_gsheet):

    lista_passeios = df_escalas_group['Servico'].unique().tolist()

    lista_passeios_tarifario = st.session_state.df_tarifario['Serviços'].unique().tolist()

    lista_passeios_sem_tarifario = [item for item in lista_passeios if not item in lista_passeios_tarifario]

    if len(lista_passeios_sem_tarifario)>0:

        df_itens_faltantes = pd.DataFrame(lista_passeios_sem_tarifario, columns=['Serviços'])

        st.dataframe(df_itens_faltantes, hide_index=True)

        nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
        credentials = service_account.Credentials.from_service_account_info(nome_credencial)
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = credentials.with_scopes(scope)
        client = gspread.authorize(credentials)
        
        spreadsheet = client.open_by_key(id_gsheet)

        sheet = spreadsheet.worksheet('Tarifário Robô')
        sheet_data = sheet.get_all_values()
        last_filled_row = len(sheet_data)
        data = df_itens_faltantes.values.tolist()
        start_row = last_filled_row + 1
        start_cell = f"A{start_row}"
        
        sheet.update(start_cell, data)

        st.error('Os serviços acima não estão tarifados. Eles foram inseridos no final da planilha de tarifários. Por favor, tarife os serviços e tente novamente')

    else:

        st.success('Todos os serviços estão tarifados!')

def definir_html(df_ref):

    html=df_ref.to_html(index=False, escape=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                text-align: center;  /* Centraliza o texto */
            }}
            table {{
                margin: 0 auto;  /* Centraliza a tabela */
                border-collapse: collapse;  /* Remove espaço entre as bordas da tabela */
            }}
            th, td {{
                padding: 8px;  /* Adiciona espaço ao redor do texto nas células */
                border: 1px solid black;  /* Adiciona bordas às células */
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    return html

def criar_output_html(nome_html, html, guia, soma_servicos):

    with open(nome_html, "w", encoding="utf-8") as file:

        file.write(f'<p style="font-size:40px;">{guia}</p><br><br>')

        file.write(html)

        file.write(f'<br><br><p style="font-size:40px;">O valor total dos serviços é {soma_servicos}</p>')

st.set_page_config(layout='wide')

if not 'df_escalas' in st.session_state:

    puxar_dados_phoenix()

st.title('Mapa de Pagamento - Guias')

st.divider()

row1 = st.columns(2)

with row1[0]:

    container_datas = st.container(border=True)

    container_datas.subheader('Período')

    data_inicial = container_datas.date_input('Data Inicial', value=None ,format='DD/MM/YYYY', key='data_inicial')

    data_final = container_datas.date_input('Data Inicial', value=None ,format='DD/MM/YYYY', key='data_final')

    gerar_mapa = container_datas.button('Gerar Mapa de Pagamentos')

with row1[1]:

    atualizar_phoenix = st.button('Atualizar Dados Phoenix')

if atualizar_phoenix:

    puxar_dados_phoenix()

st.divider()

if gerar_mapa and data_inicial and data_final:

    puxar_tarifarios()

    df_escalas = st.session_state.df_escalas[(st.session_state.df_escalas['Data da Escala'] >= data_inicial) & (st.session_state.df_escalas['Data da Escala'] <= data_final)].reset_index(drop=True)

    df_escalas_group = df_escalas.groupby(['Data da Escala', 'Escala', 'Veiculo', 'Motorista', 'Guia', 'Servico', 'Tipo de Servico', 'Modo'])\
        .agg({'Apoio': 'first',  'Observacao': avaliar_observacao, 'Idioma': avaliar_idioma}).reset_index()

    df_escalas_group = df_escalas_group.rename(columns=({'Observacao': 'Barco Carneiros', 'Veiculo': 'Veículo'}))

    verificar_tarifarios(df_escalas_group, '1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE')

    df_escalas_group = pd.merge(df_escalas_group, st.session_state.df_tarifario, left_on='Servico', right_on='Serviços', how='left')

    df_escalas_group = df_escalas_group.drop(columns='Serviços')

    df_escalas_group['Motoguia'] = ''

    df_escalas_group.loc[df_escalas_group['Idioma']=='X', 'Valor Final'] = df_escalas_group['Valor Idioma']

    df_escalas_group.loc[df_escalas_group['Idioma']=='', 'Valor Final'] = df_escalas_group['Valor']

    df_escalas_group.loc[df_escalas_group['Motorista']==df_escalas_group['Guia'], ['Motoguia', 'Valor']] = ['X', 250]

    df_escalas_group['Valor Final'] = df_escalas_group['Valor Final'] + df_escalas_group['Barco Carneiros']

    st.session_state.df_pag_final = df_escalas_group[['Data da Escala', 'Modo', 'Tipo de Servico', 'Servico', 'Veículo', 'Motorista', 'Guia', 'Motoguia', 'Idioma', 'Barco Carneiros', 'Valor Final']]

if 'df_pag_final' in st.session_state:

    st.header('Gerar Mapas')

    row2 = st.columns(2)

    with row2[0]:

        lista_guias = st.session_state.df_pag_final['Guia'].dropna().unique().tolist()

        guia = st.selectbox('Guia', sorted(lista_guias), index=None)

    if guia:

        row2_1 = st.columns(2)

        df_pag_guia = st.session_state.df_pag_final[st.session_state.df_pag_final['Guia']==guia].sort_values(by=['Data da Escala', 'Veículo', 'Motorista']).reset_index(drop=True)

        df_data_correta = df_pag_guia.reset_index(drop=True)

        df_data_correta['Data da Escala'] = pd.to_datetime(df_data_correta['Data da Escala'])

        df_data_correta['Data da Escala'] = df_data_correta['Data da Escala'].dt.strftime('%d/%m/%Y')

        container_dataframe = st.container()

        container_dataframe.dataframe(df_data_correta, hide_index=True, use_container_width = True)

        with row2_1[0]:

            total_a_pagar = df_pag_guia['Valor'].sum()

            st.subheader(f'Valor Total: R${int(total_a_pagar)}')

        df_pag_guia['Data da Escala'] = pd.to_datetime(df_pag_guia['Data da Escala'])

        df_pag_guia['Data da Escala'] = df_pag_guia['Data da Escala'].dt.strftime('%d/%m/%Y')

        soma_servicos = df_pag_guia['Valor'].sum()

        soma_servicos = format_currency(soma_servicos, 'BRL', locale='pt_BR')

        for item in ['Valor']:

            df_pag_guia[item] = df_pag_guia[item].apply(lambda x: format_currency(x, 'BRL', locale='pt_BR'))

        html = definir_html(df_pag_guia)

        nome_html = f'{guia}.html'

        criar_output_html(nome_html, html, guia, soma_servicos)

        with open(nome_html, "r", encoding="utf-8") as file:

            html_content = file.read()

        with row2_1[1]:

            st.download_button(
                label="Baixar Arquivo HTML",
                data=html_content,
                file_name=nome_html,
                mime="text/html"
            )
