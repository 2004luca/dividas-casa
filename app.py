import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configurações Iniciais
st.set_page_config(page_title="Dívidas da Casa", layout="centered")
MORADORES = ["Luca", "Luiza", "Helena", "Zé"]

# Conexão com o Google Sheets
# Nota: Você precisará configurar as "Secrets" no Streamlit Cloud depois
conn = st.connection("gsheets", type=GSheetsConnection)

def ler_dados():
    return conn.read(ttl="0s") # ttl=0 para sempre pegar o dado mais fresco

def salvar_dados(df_atualizado):
    conn.update(data=df_atualizado)
    st.cache_data.clear()

# Carregar dados atuais
df = ler_dados()

# --- LÓGICA DE CÁLCULO ---
def calcular_saldos(df_transacoes):
    saldos = {m: {outra: 0.0 for outra in MORADORES if outra != m} for m in MORADORES}
    
    for _, row in df_transacoes.iterrows():
        pagador = row['Pagador']
        valor = float(row['Valor'])
        tipo = row['Tipo']
        beneficiados = row['Beneficiados'].split(", ")
        
        if tipo == "Gasto":
            valor_por_pessoa = valor / len(beneficiados)
            for pessoa in beneficiados:
                if pessoa != pagador:
                    saldos[pessoa][pagador] += valor_por_pessoa
        elif tipo == "Pagamento":
            recebedor = beneficiados[0]
            saldos[pagador][recebedor] -= valor
    return saldos

# --- INTERFACE ---
st.title("💰 Controle de Dívidas da Casa")

# Sidebar para novos registros
with st.sidebar.form("novo_registro"):
    st.header("Novo Registro")
    tipo_op = st.radio("Ação", ["Registrar Gasto", "Pagar Dívida"])
    quem = st.selectbox("Quem pagou?", MORADORES)
    quanto = st.number_input("Valor (€)", min_value=0.01)
    
    if tipo_op == "Registrar Gasto":
        para = st.multiselect("Para quem?", MORADORES, default=MORADORES)
    else:
        para = [st.selectbox("Pagou para quem?", [m for m in MORADORES if m != quem])]
    
    enviar = st.form_submit_button("Salvar na Planilha")

if enviar:
    nova_linha = pd.DataFrame([{
        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Pagador": quem,
        "Valor": quanto,
        "Beneficiados": ", ".join(para),
        "Tipo": "Gasto" if tipo_op == "Registrar Gasto" else "Pagamento"
    }])
    df_final = pd.concat([df, nova_linha], ignore_index=True)
    salvar_dados(df_final)
    st.success("Dados enviados para o Google Sheets!")
    st.rerun()

# Dashboard
st.subheader("📋 Resumo Atual")
if not df.empty:
    saldos = calcular_saldos(df)
    for devedor, credores in saldos.items():
        for credor, valor in credores.items():
            if valor > 0.01:
                st.error(f"🔴 **{devedor}** deve **{valor:.2f}€** para **{credor}**")
            elif valor < -0.01:
                st.success(f"🟢 **{credor}** deve **{abs(valor):.2f}€** para **{devedor}**")
else:
    st.info("Nenhuma conta registrada ainda.")

with st.expander("Ver Histórico Completo"):
    st.dataframe(df)
