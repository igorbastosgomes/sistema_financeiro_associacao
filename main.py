import streamlit as st
import sqlite3
import pandas as pd

# Banco de dados
conn = sqlite3.connect('financeiro_associacao_novo.db', check_same_thread=False)
cursor = conn.cursor()

st.set_page_config(page_title="Sistema Financeiro", layout="wide")
st.title("💼 Sistema Financeiro da Associação")

menu = st.sidebar.radio("Menu", ["Novo Lançamento", "Visualizar Lançamentos", "Plano de Contas", "Centros de Custo"])

# Funções auxiliares
def get_centros_custo():
    return pd.read_sql_query("SELECT codigo, nome FROM centros_custo", conn)

def get_planos():
    return pd.read_sql_query("SELECT DISTINCT plano_conta FROM itens_lancamento", conn)

# Aba - Novo lançamento com múltiplos itens
if menu == "Novo Lançamento":
    st.header("📝 Novo Lançamento")

    with st.form("form_lancamento"):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data")
            vencimento = st.date_input("Vencimento")
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            fornecedor = st.text_input("Fornecedor")
        with col2:
            documento = st.text_input("Nº Documento")
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Pix", "Boleto", "Transferência", "Dinheiro", "Cartão"])
            parcelas = st.number_input("Parcelas", min_value=1, value=1)
            custo_fixo = st.checkbox("Custo Fixo (Contrato)?")

        st.markdown("### Rateio por Plano de Contas e Centro de Custo")

        centros_df = get_centros_custo()
        n_itens = st.number_input("Quantos itens deseja incluir?", min_value=1, value=2)

        rateios = []
        total = 0
        for i in range(int(n_itens)):
            st.markdown(f"**Item {i+1}**")
            col1, col2, col3 = st.columns([3, 3, 2])
            with col1:
                plano = st.text_input(f"Plano de Contas - Item {i+1}", key=f"plano_{i}")
            with col2:
                centro = st.selectbox(f"Centro de Custo - Item {i+1}", centros_df['nome'].tolist(), key=f"centro_{i}")
            with col3:
                valor = st.number_input(f"Valor - Item {i+1}", min_value=0.0, step=0.01, key=f"valor_{i}")
            rateios.append((plano, centro, valor))
            total += valor

        st.markdown(f"**Valor total rateado:** R$ {total:,.2f}")

        valor_total_lancamento = st.number_input("Valor total da nota (para conferência)", min_value=0.0, step=0.01)

        submitted = st.form_submit_button("Salvar Lançamento")

        if submitted:
            if abs(total - valor_total_lancamento) > 0.01:
                st.error("⚠️ A soma dos itens não bate com o valor total informado.")
            else:
                cursor.execute("""
                    INSERT INTO lancamentos (
                        data, fornecedor, documento, tipo,
                        forma_pagamento, parcelas, custo_fixo, vencimento, valor_total
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (data, fornecedor, documento, tipo, forma_pagamento, parcelas, int(custo_fixo), vencimento, valor_total_lancamento))
                lancamento_id = cursor.lastrowid

                for plano, centro, valor in rateios:
                    cursor.execute("""
                        INSERT INTO itens_lancamento (id_lancamento, centro_custo, plano_conta, valor)
                        VALUES (?, ?, ?, ?)
                    """, (lancamento_id, centro, plano, valor))

                conn.commit()
                st.success("✅ Lançamento salvo com sucesso!")

# Aba - Visualizar lançamentos
elif menu == "Visualizar Lançamentos":
    st.header("📊 Lançamentos Cadastrados")
    df = pd.read_sql_query("""
        SELECT l.id, l.data, l.fornecedor, l.documento, l.tipo, l.forma_pagamento,
               l.custo_fixo, l.valor_total, i.plano_conta, i.centro_custo, i.valor
        FROM lancamentos l
        JOIN itens_lancamento i ON l.id = i.id_lancamento
        ORDER BY l.data DESC
    """, conn)
    st.dataframe(df)

# Aba - Visualizar Centros de Custo
elif menu == "Centros de Custo":
    st.header("🏷️ Centros de Custo Cadastrados")
    df = get_centros_custo()
    st.dataframe(df)

# Aba - Plano de Contas (consulta simples)
elif menu == "Plano de Contas":
    st.header("📚 Planos de Contas Usados")
    df = get_planos()
    st.dataframe(df)
