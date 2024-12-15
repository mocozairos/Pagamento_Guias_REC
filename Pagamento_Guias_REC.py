import streamlit as st
import pandas as pd
import mysql.connector
import decimal
from babel.numbers import format_currency
from google.oauth2 import service_account
import gspread 
import requests

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

def puxar_aba_simples(id_gsheet, nome_aba, nome_df):

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(id_gsheet)
    
    sheet = spreadsheet.worksheet(nome_aba)

    sheet_data = sheet.get_all_values()

    st.session_state[nome_df] = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

def puxar_programacao_passeios():

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE')
    
    sheet = spreadsheet.worksheet('Programação Passeios Espanhol')

    sheet_data = sheet.get_all_values()

    st.session_state.df_programacao_passeios_espanhol = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

    st.session_state.df_programacao_passeios_espanhol["Serviço"] = st.session_state.df_programacao_passeios_espanhol["Serviço"].apply(lambda x: x.split(' & '))

    st.session_state.df_programacao_passeios_espanhol['Data da Escala'] = pd.to_datetime(st.session_state.df_programacao_passeios_espanhol['Data da Escala'], format='%d/%m/%y')

    st.session_state.df_programacao_passeios_espanhol['Data da Escala'] = st.session_state.df_programacao_passeios_espanhol['Data da Escala'].dt.date

def puxar_apoios_box():

    puxar_aba_simples('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE', 'Apoios ao Box', 'df_apoios_box')

    st.session_state.df_apoios_box['Data da Escala'] = pd.to_datetime(st.session_state.df_apoios_box['Data da Escala'], format='%d/%m/%Y')

    st.session_state.df_apoios_box['Data da Escala'] = st.session_state.df_apoios_box['Data da Escala'].dt.date

    st.session_state.df_apoios_box['Tipo de Apoio (H ou F)'] = st.session_state.df_apoios_box['Tipo de Apoio (H ou F)'].replace('F', 'APOIO AO BOX FULL')

    st.session_state.df_apoios_box['Tipo de Apoio (H ou F)'] = st.session_state.df_apoios_box['Tipo de Apoio (H ou F)'].replace('H', 'APOIO AO BOX HALF')

    st.session_state.df_apoios_box = st.session_state.df_apoios_box.rename(columns={'Tipo de Apoio (H ou F)': 'Servico'})

    st.session_state.df_apoios_box[['Modo', 'Tipo de Servico', 'Veículo', 'Motorista', 'Motoguia', 'Idioma', 'Apenas Recepcao', 'Barco Carneiros', 'Valor Final']] = \
        ['REGULAR', 'APOIO', '', '', '', '', '', 0, 0]

    st.session_state.df_apoios_box.loc[st.session_state.df_apoios_box['Servico']=='APOIO AO BOX FULL', 'Valor Final'] = 162

    st.session_state.df_apoios_box.loc[st.session_state.df_apoios_box['Servico']=='APOIO AO BOX HALF', 'Valor Final'] = 138

    st.session_state.df_apoios_box = st.session_state.df_apoios_box[['Data da Escala', 'Modo', 'Tipo de Servico', 'Servico', 'Veículo', 'Motorista', 'Guia', 'Motoguia', 'Idioma', 'Apenas Recepcao', 
                                                                     'Barco Carneiros', 'Valor Final']]

def avaliar_observacao(observacoes):

    return 50 if 'barco_carneiros' in observacoes else 0

def avaliar_idioma(idiomas):

    return 'X' if any(idioma != 'pt-br' for idioma in idiomas) else ''

def verificar_tarifarios(df_escalas_group, id_gsheet):

    lista_passeios = df_escalas_group['Servico'].unique().tolist()

    lista_passeios_tarifario = st.session_state.df_tarifario['Servico'].unique().tolist()

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

def identificar_passeios_regulares_saindo_de_porto(df_escalas_group):

    for index in range(len(df_escalas_group)):

        passeio_ref = df_escalas_group.at[index, 'Servico']

        tipo_servico_ref = df_escalas_group.at[index, 'Tipo de Servico']

        modo_servico = df_escalas_group.at[index, 'Modo']

        if '(PORTO DE GALINHAS)' in passeio_ref and tipo_servico_ref=='TOUR' and modo_servico=='REGULAR':

            df_escalas_group.at[index, 'Passeios Saindo de Porto']='X'

        else:

            df_escalas_group.at[index, 'Passeios Saindo de Porto']=''      

    return df_escalas_group

def filtrando_idiomas_passeios_programacao_espanhol(df_escalas_group):

    df_escalas_saindo_de_porto_idioma = df_escalas_group[(df_escalas_group['Idioma']=='X') & (df_escalas_group['Passeios Saindo de Porto']=='X')].reset_index()

    for index, index_principal in df_escalas_saindo_de_porto_idioma['index'].items():

        data_da_escala = df_escalas_saindo_de_porto_idioma.at[index, 'Data da Escala']

        passeio_ref = df_escalas_saindo_de_porto_idioma.at[index, 'Servico']

        lista_passeios_espanhol = st.session_state.df_programacao_passeios_espanhol.loc[st.session_state.df_programacao_passeios_espanhol['Data da Escala']==data_da_escala, 'Serviço'].iloc[0]

        if not (passeio_ref in lista_passeios_espanhol):

            df_escalas_group.at[index_principal, 'Idioma'] = ''

    return df_escalas_group

def verificar_guia_sem_telefone(id_gsheet, guia, lista_guias_com_telefone):

    if not guia in lista_guias_com_telefone:

        lista_guias = []

        lista_guias.append(guia)

        df_itens_faltantes = pd.DataFrame(lista_guias, columns=['Guias'])

        st.dataframe(df_itens_faltantes, hide_index=True)

        nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
        credentials = service_account.Credentials.from_service_account_info(nome_credencial)
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = credentials.with_scopes(scope)
        client = gspread.authorize(credentials)
        
        spreadsheet = client.open_by_key(id_gsheet)

        sheet = spreadsheet.worksheet('Telefones Guias')
        sheet_data = sheet.get_all_values()
        last_filled_row = len(sheet_data)
        data = df_itens_faltantes.values.tolist()
        start_row = last_filled_row + 1
        start_cell = f"A{start_row}"
        
        sheet.update(start_cell, data)

        st.error(f'O guia {guia} não tem número de telefone cadastrado na planilha. Ele foi inserido no final da lista de guias. Por favor, cadastre o telefone dele e tente novamente')

        st.stop()

    else:

        telefone_guia = st.session_state.df_telefones.loc[st.session_state.df_telefones['Guias']==guia, 'Telefone'].values[0]

    return telefone_guia

def calculo_diarias_motoguias_trf(df_escalas_group):

    df_escalas_motoguias_trf = df_escalas_group[(df_escalas_group['Motoguia']=='X') & (df_escalas_group['Tipo de Servico'].isin(['OUT', 'IN']))].reset_index()

    for index, data_da_escala in df_escalas_motoguias_trf['Data da Escala'].items():

        guia_referencia = df_escalas_motoguias_trf.at[index, 'Guia']

        df_guia_data = df_escalas_group[(df_escalas_group['Data da Escala']==data_da_escala) & (df_escalas_group['Guia']==guia_referencia)].reset_index()

        if len(df_guia_data)>1:

            for index_2, index_principal in df_guia_data['index'].items():

                if index_2>0:

                    df_escalas_group.at[index_principal, 'Valor Final'] = 0

    return df_escalas_group

def retirar_passeios_repetidos(df_escalas_group):

    df_escalas_passeios_repetidos = df_escalas_group[df_escalas_group['Tipo de Servico']=='TOUR'].groupby(['Data da Escala', 'Veículo', 'Motorista', 'Guia', 'Servico'])['Escala'].count().reset_index()

    df_escalas_passeios_repetidos = df_escalas_passeios_repetidos[df_escalas_passeios_repetidos['Escala']>1].reset_index(drop=True)

    for index in range(len(df_escalas_passeios_repetidos)):

        data_da_escala = df_escalas_passeios_repetidos.at[index, 'Data da Escala']

        veiculo_ref = df_escalas_passeios_repetidos.at[index, 'Veículo']

        motorista_ref = df_escalas_passeios_repetidos.at[index, 'Motorista']

        guia_referencia = df_escalas_passeios_repetidos.at[index, 'Guia']

        servico_ref = df_escalas_passeios_repetidos.at[index, 'Servico']

        df_ref = df_escalas_group[(df_escalas_group['Data da Escala']==data_da_escala) & (df_escalas_group['Veículo']==veiculo_ref) & (df_escalas_group['Motorista']==motorista_ref) & 
                                  (df_escalas_group['Guia']==guia_referencia) & (df_escalas_group['Servico']==servico_ref)].reset_index()
        
        for index_2, index_principal in df_ref['index'].items():

            if index_2>0:

                df_escalas_group = df_escalas_group.drop(index=index_principal)
        
    df_escalas_group = df_escalas_group.reset_index(drop=True)

    return df_escalas_group

def precificar_extra_barco_carneiros(df_escalas_group):

    df_escalas_group['Barco Carneiros'] = 0

    lista_escalas_extra_barco = st.session_state.df_extra_barco['Escala'].unique().tolist()

    df_escalas_group.loc[df_escalas_group['Escala'].isin(lista_escalas_extra_barco), 'Barco Carneiros'] = 50

    return df_escalas_group

def precificar_apenas_recepcao(df_escalas_group):

    df_escalas_group['Apenas Recepcao'] = ''

    lista_escalas_apenas_recepcao = st.session_state.df_apenas_recepcao['Escala'].unique().tolist()

    df_escalas_group.loc[df_escalas_group['Escala'].isin(lista_escalas_apenas_recepcao), ['Apenas Recepcao', 'Valor Final']] = ['X', 56]

    return df_escalas_group

def puxar_servicos_navio():

    puxar_aba_simples('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE', 'Serviço de Guia - Navio', 'df_servicos_navio')

    st.session_state.df_servicos_navio['Data da Escala'] = pd.to_datetime(st.session_state.df_servicos_navio['Data da Escala'], format='%d/%m/%Y')

    st.session_state.df_servicos_navio['Data da Escala'] = st.session_state.df_servicos_navio['Data da Escala'].dt.date

    st.session_state.df_servicos_navio[['Modo', 'Tipo de Servico', 'Servico', 'Veículo', 'Motorista', 'Motoguia', 'Idioma', 'Apenas Recepcao', 'Barco Carneiros', 'Valor Final']] = \
        ['REGULAR', 'TOUR', 'Serviço de Guia - Navio', '', '', '', '', '', 0, 194]

    st.session_state.df_servicos_navio = st.session_state.df_servicos_navio[['Data da Escala', 'Modo', 'Tipo de Servico', 'Servico', 'Veículo', 'Motorista', 'Guia', 'Motoguia', 'Idioma', 
                                                                             'Apenas Recepcao', 'Barco Carneiros', 'Valor Final']]

st.set_page_config(layout='wide')

with st.spinner('Puxando dados do Phoenix...'):

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

    puxar_programacao_passeios()

    puxar_aba_simples('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE', 'Extra Barco', 'df_extra_barco')

    puxar_aba_simples('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE', 'Apenas Recepção', 'df_apenas_recepcao')

    puxar_apoios_box()

    puxar_servicos_navio()

    df_escalas = st.session_state.df_escalas[(st.session_state.df_escalas['Data da Escala'] >= data_inicial) & (st.session_state.df_escalas['Data da Escala'] <= data_final)].reset_index(drop=True)

    df_escalas.loc[df_escalas['Adicional'].str.contains('GUIA BILINGUE', na=False), 'Idioma'] = 'en-us'
    
    df_escalas_group = df_escalas.groupby(['Data da Escala', 'Escala', 'Veiculo', 'Motorista', 'Guia', 'Servico', 'Tipo de Servico', 'Modo'])\
        .agg({'Apoio': 'first',  'Idioma': avaliar_idioma}).reset_index()

    df_escalas_group = df_escalas_group.rename(columns=({'Observacao': 'Barco Carneiros', 'Veiculo': 'Veículo'}))

    verificar_tarifarios(df_escalas_group, '1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE')

    df_escalas_group = identificar_passeios_regulares_saindo_de_porto(df_escalas_group)

    df_escalas_group = filtrando_idiomas_passeios_programacao_espanhol(df_escalas_group)

    df_escalas_group = pd.merge(df_escalas_group, st.session_state.df_tarifario, on='Servico', how='left')

    df_escalas_group['Motoguia'] = ''

    df_escalas_group.loc[df_escalas_group['Idioma']=='X', 'Valor Final'] = df_escalas_group['Valor Idioma']

    df_escalas_group.loc[df_escalas_group['Idioma']=='', 'Valor Final'] = df_escalas_group['Valor']

    df_escalas_group.loc[df_escalas_group['Motorista']==df_escalas_group['Guia'], ['Motoguia', 'Valor Final']] = ['X', 250]

    df_escalas_group = calculo_diarias_motoguias_trf(df_escalas_group)

    df_escalas_group = retirar_passeios_repetidos(df_escalas_group)

    df_escalas_group = precificar_extra_barco_carneiros(df_escalas_group)

    df_escalas_group = precificar_apenas_recepcao(df_escalas_group)

    df_escalas_group['Valor Final'] = df_escalas_group['Valor Final'] + df_escalas_group['Barco Carneiros']

    st.session_state.df_pag_final = df_escalas_group[['Data da Escala', 'Modo', 'Tipo de Servico', 'Servico', 'Veículo', 'Motorista', 'Guia', 'Motoguia', 'Idioma', 'Apenas Recepcao', 'Barco Carneiros', 
                                                      'Valor Final']]

    st.session_state.df_pag_final = pd.concat([st.session_state.df_pag_final, st.session_state.df_apoios_box, st.session_state.df_servicos_navio], ignore_index=True)

if 'df_pag_final' in st.session_state:

    st.header('Gerar Mapas')

    row2 = st.columns(2)

    with row2[0]:

        lista_guias = st.session_state.df_pag_final[st.session_state.df_pag_final['Guia']!='NENHUM GUIA']['Guia'].dropna().unique().tolist()

        guia = st.selectbox('Guia', sorted(lista_guias), index=None)

    if guia:

        row2_1 = st.columns(4)

        df_pag_guia = st.session_state.df_pag_final[st.session_state.df_pag_final['Guia']==guia].sort_values(by=['Data da Escala', 'Veículo', 'Motorista']).reset_index(drop=True)

        df_data_correta = df_pag_guia.reset_index(drop=True)

        df_data_correta['Data da Escala'] = pd.to_datetime(df_data_correta['Data da Escala'])

        df_data_correta['Data da Escala'] = df_data_correta['Data da Escala'].dt.strftime('%d/%m/%Y')

        container_dataframe = st.container()

        container_dataframe.dataframe(df_data_correta, hide_index=True, use_container_width = True)

        with row2_1[0]:

            total_a_pagar = df_pag_guia['Valor Final'].sum()

            st.subheader(f'Valor Total: R${int(total_a_pagar)}')

        df_pag_guia['Data da Escala'] = pd.to_datetime(df_pag_guia['Data da Escala'])

        df_pag_guia['Data da Escala'] = df_pag_guia['Data da Escala'].dt.strftime('%d/%m/%Y')

        soma_servicos = df_pag_guia['Valor Final'].sum()

        soma_servicos = format_currency(soma_servicos, 'BRL', locale='pt_BR')

        for item in ['Valor Final', 'Barco Carneiros']:

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

        st.session_state.html_content = html_content

    else:

        row2_1 = st.columns(4)

        with row2_1[0]:

            enviar_informes = st.button(f'Enviar Informes Gerais')

            if enviar_informes:

                puxar_aba_simples('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE', 'Telefones Guias', 'df_telefones')

                lista_htmls = []

                lista_telefones = []

                for guia_ref in lista_guias:

                    telefone_guia = verificar_guia_sem_telefone('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE', guia_ref, st.session_state.df_telefones['Guias'].unique().tolist())

                    df_pag_guia = st.session_state.df_pag_final[st.session_state.df_pag_final['Guia']==guia_ref].sort_values(by=['Data da Escala', 'Veículo', 'Motorista']).reset_index(drop=True)

                    df_pag_guia['Data da Escala'] = pd.to_datetime(df_pag_guia['Data da Escala'])

                    df_pag_guia['Data da Escala'] = df_pag_guia['Data da Escala'].dt.strftime('%d/%m/%Y')

                    soma_servicos = df_pag_guia['Valor Final'].sum()

                    soma_servicos = format_currency(soma_servicos, 'BRL', locale='pt_BR')

                    for item in ['Valor Final', 'Barco Carneiros']:

                        df_pag_guia[item] = df_pag_guia[item].apply(lambda x: format_currency(x, 'BRL', locale='pt_BR'))

                    html = definir_html(df_pag_guia)

                    nome_html = f'{guia_ref}.html'

                    criar_output_html(nome_html, html, guia_ref, soma_servicos)

                    with open(nome_html, "r", encoding="utf-8") as file:

                        html_content_guia_ref = file.read()

                    lista_htmls.append([html_content_guia_ref, telefone_guia])

                webhook_thiago = "https://conexao.multiatend.com.br/webhook/pagamentoluckrecife"

                payload = {"informe_html": lista_htmls}
                
                response = requests.post(webhook_thiago, json=payload)
                    
                if response.status_code == 200:
                    
                    st.success(f"Mapas de Pagamentos enviados com sucesso!")
                    
                else:
                    
                    st.error(f"Erro. Favor contactar o suporte")

                    st.error(f"{response}")

if 'html_content' in st.session_state and guia:

    with row2_1[2]:

        enviar_informes = st.button(f'Enviar Informes | {guia}')

    if enviar_informes:

        puxar_aba_simples('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE', 'Telefones Guias', 'df_telefones')

        telefone_guia = verificar_guia_sem_telefone('1RwFPP9nQttGztxicHeJGTG6UqoL7fPKCWSdhhEdRVhE', guia, st.session_state.df_telefones['Guias'].unique().tolist())

        webhook_thiago = "https://conexao.multiatend.com.br/webhook/pagamentoluckrecife"
        
        payload = {"informe_html": st.session_state.html_content, 
                    "telefone": telefone_guia}
        
        response = requests.post(webhook_thiago, json=payload)
            
        if response.status_code == 200:
            
            st.success(f"Mapas de Pagamento enviados com sucesso!")
            
        else:
            
            st.error(f"Erro. Favor contactar o suporte")

            st.error(f"{response}")
