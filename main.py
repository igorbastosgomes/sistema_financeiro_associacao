import streamlit as st
import sqlite3
import pandas as pd

conn = sqlite3.connect('sistema_associacao_completo.db', check_same_thread=False)
cursor = conn.cursor()

st.set_page_config(layout="wide")
st.title("📘 Sistema Financeiro da Associação")

# Funções auxiliares
def get_centros_custo():
    return pd.read_sql_query("SELECT id, nome FROM centros_custo", conn)

def listar_planos_base():
    return pd.read_sql_query("SELECT * FROM planos_contas", conn)

def listar_planos_completos():
    return pd.read_sql_query("""
        SELECT ppc.codigo_completo, pc.descricao, cc.nome as centro_custo
        FROM planos_por_centro ppc
        JOIN planos_contas pc ON pc.id = ppc.plano_base_id
        JOIN centros_custo cc ON cc.id = ppc.centro_custo_id
        ORDER BY ppc.codigo_completo
    """, conn)

def listar_fornecedores():
    return pd.read_sql_query("SELECT * FROM fornecedores", conn)

def listar_planos_por_centro():
    return pd.read_sql_query("""
        SELECT ppc.id, ppc.codigo_completo, pc.descricao, cc.nome as centro
        FROM planos_por_centro ppc
        JOIN planos_contas pc ON ppc.plano_base_id = pc.id
        JOIN centros_custo cc ON ppc.centro_custo_id = cc.id
    """, conn)

# MENU
aba = st.sidebar.radio("Menu", ["Cadastrar Plano", "Ver Planos Cadastrados", "Centros de Custo", "Fornecedores", "Lançamentos", "Relatórios e Dashboards"])

# Cadastro de plano de contas base
if aba == "Cadastrar Plano":
    st.header("🧾 Novo Plano de Contas Base")
    col1, col2, col3 = st.columns(3)
    with col1:
        grupo = st.number_input("Grupo", min_value=1, max_value=9, step=1)
    with col2:
        subgrupo = st.number_input("Subgrupo", min_value=0, max_value=99, step=1)
    with col3:
        item = st.number_input("Item", min_value=0, max_value=99, step=1)

    descricao = st.text_input("Descrição")

    if st.button("Cadastrar Plano para todos os centros de custo"):
        if not descricao:
            st.error("Preencha todos os campos obrigatórios.")
        else:
            cursor.execute("""
                INSERT INTO planos_contas (grupo, subgrupo, item, descricao)
                VALUES (?, ?, ?, ?)
            """, (grupo, subgrupo, item, descricao))
            plano_id = cursor.lastrowid

            centros_df = get_centros_custo()
            for _, row in centros_df.iterrows():
                centro_id = row['id']
                codigo = f"{grupo}.{subgrupo}.{item}.{centro_id}"
                cursor.execute("""
                    INSERT INTO planos_por_centro (plano_base_id, centro_custo_id, codigo_completo)
                    VALUES (?, ?, ?)
                """, (plano_id, centro_id, codigo))

            conn.commit()
            st.success("Plano cadastrado com sucesso para todos os centros de custo.")

# Visualização dos planos cadastrados
elif aba == "Ver Planos Cadastrados":
    st.header("📂 Planos de Contas por Centro de Custo")
    df = listar_planos_completos()
    st.dataframe(df, use_container_width=True)

# Edição de centros de custo
elif aba == "Centros de Custo":
    st.header("🏷️ Editar Centros de Custo")
    centros_df = get_centros_custo()
    st.dataframe(centros_df)

    with st.form("novo_centro"):
        novo_nome = st.text_input("Novo centro de custo")
        if st.form_submit_button("Adicionar"):
            if novo_nome.strip():
                cursor.execute("INSERT OR IGNORE INTO centros_custo (nome) VALUES (?)", (novo_nome.strip(),))
                conn.commit()
                st.success("Centro de custo adicionado.")
            else:
                st.warning("Digite um nome válido.")

# Cadastro de fornecedores
elif aba == "Fornecedores":
    st.header("🏢 Cadastro de Fornecedores")
    with st.form("cadastro_fornecedor"):
        nome = st.text_input("Nome do fornecedor")
        cnpj = st.text_input("CNPJ")
        email = st.text_input("Email")
        telefone = st.text_input("Telefone")
        if st.form_submit_button("Cadastrar"):
            if nome:
                cursor.execute("""
                    INSERT INTO fornecedores (nome, cnpj, email, telefone)
                    VALUES (?, ?, ?, ?)
                """, (nome, cnpj, email, telefone))
                conn.commit()
                st.success("Fornecedor cadastrado com sucesso.")
            else:
                st.warning("O nome do fornecedor é obrigatório.")

    st.subheader("📋 Fornecedores cadastrados")
    fornecedores_df = listar_fornecedores()
    st.dataframe(fornecedores_df, use_container_width=True)

# Lançamentos
elif aba == "Lançamentos":
    st.header("💰 Lançar Despesa")
    with st.form("form_lancamento"):
        data = st.date_input("Data")
        fornecedores_df = listar_fornecedores()
        fornecedor = st.selectbox("Fornecedor", fornecedores_df['nome'].tolist())
        doc = st.text_input("Documento")
        descricao = st.text_input("Descrição da nota")
        valor_total = st.number_input("Valor total", min_value=0.0, step=0.01)
        forma_pagamento = st.selectbox("Forma de Pagamento", ["Pix", "Boleto", "Transferência", "Dinheiro"])
        parcelas = st.number_input("Parcelas", min_value=1, step=1, value=1)
        contrato = st.checkbox("É um contrato mensal?")
        vencimento = st.date_input("Vencimento")
        imposto_retido = st.checkbox("Há retenções de imposto?")

        planos_df = listar_planos_por_centro()
        st.markdown("### Rateio da Nota")
        rateio = []
        for i in range(3):
            col1, col2 = st.columns([4, 1])
            with col1:
                plano = st.selectbox(f"Plano {i+1}", planos_df['codigo_completo'].tolist(), key=f"plano_{i}")
            with col2:
                valor = st.number_input(f"Valor {i+1}", min_value=0.0, step=0.01, key=f"valor_{i}")
            rateio.append((plano, valor))

        if st.form_submit_button("Salvar Lançamento"):
            fornecedor_id = fornecedores_df[fornecedores_df['nome'] == fornecedor]['id'].values[0]
            cursor.execute("""
                INSERT INTO lancamentos (data, fornecedor_id, documento, descricao, valor_total, forma_pagamento,
                parcelas, contrato, vencimento, imposto_retido)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data, fornecedor_id, doc, descricao, valor_total, forma_pagamento, parcelas, contrato, vencimento, imposto_retido))
            lancamento_id = cursor.lastrowid

            for plano_cod, valor in rateio:
                plano_id = planos_df[planos_df['codigo_completo'] == plano_cod]['id'].values[0]
                cursor.execute("""
                    INSERT INTO itens_lancamento (id_lancamento, plano_centro_id, valor)
                    VALUES (?, ?, ?)
                """, (lancamento_id, plano_id, valor))

            conn.commit()
            st.success("Lançamento registrado com sucesso!")

# Relatórios e Dashboards
elif aba == "Relatórios e Dashboards":
    st.header("📊 Prestação de Contas e Gráficos")
    df = pd.read_sql_query("""
        SELECT cc.nome AS centro, pc.descricao, ppc.codigo_completo, il.valor
        FROM itens_lancamento il
        JOIN planos_por_centro ppc ON il.plano_centro_id = ppc.id
        JOIN planos_contas pc ON ppc.plano_base_id = pc.id
        JOIN centros_custo cc ON ppc.centro_custo_id = cc.id
    """, conn)

    st.subheader("Resumo por Centro de Custo")
    resumo_centro = df.groupby("centro")["valor"].sum().reset_index()
    st.dataframe(resumo_centro)

    st.subheader("Resumo por Categoria")
    resumo_categoria = df.groupby("descricao")["valor"].sum().reset_index()
    st.dataframe(resumo_categoria)

    st.subheader("Gráfico Donut por Centro de Custo")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.pie(resumo_centro['valor'], labels=resumo_centro['centro'], wedgeprops=dict(width=0.4))
    ax.set(aspect="equal")
    st.pyplot(fig)

    st.subheader("Gráfico Donut por Categoria")
    fig2, ax2 = plt.subplots()
    ax2.pie(resumo_categoria['valor'], labels=resumo_categoria['descricao'], wedgeprops=dict(width=0.4))
    ax2.set(aspect="equal")
    st.pyplot(fig2)


