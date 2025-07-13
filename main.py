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

# MENU
aba = st.sidebar.radio("Menu", ["Cadastrar Plano", "Ver Planos Cadastrados", "Centros de Custo", "Fornecedores"])

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

    centros_df = get_centros_custo()
    centros_selecionados = st.multiselect(
        "Selecionar centros de custo para aplicar esse plano",
        centros_df['nome'].tolist()
    )

    if st.button("Cadastrar Plano"):
        if not descricao or not centros_selecionados:
            st.error("Preencha todos os campos e selecione pelo menos um centro de custo.")
        else:
            cursor.execute("""
                INSERT INTO planos_contas (grupo, subgrupo, item, descricao)
                VALUES (?, ?, ?, ?)
            """, (grupo, subgrupo, item, descricao))
            plano_id = cursor.lastrowid

            for nome in centros_selecionados:
                centro_id = centros_df[centros_df['nome'] == nome]['id'].values[0]
                codigo = f"{grupo}.{subgrupo}.{item}.{centro_id}"
                cursor.execute("""
                    INSERT INTO planos_por_centro (plano_base_id, centro_custo_id, codigo_completo)
                    VALUES (?, ?, ?)
                """, (plano_id, centro_id, codigo))

            conn.commit()
            st.success("Plano cadastrado com sucesso para os centros selecionados.")

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

