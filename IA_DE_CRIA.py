#Bibliotecas usadas no sistema.
import streamlit as st
import google.generativeai as genai
import sqlite3

#Limpar conversa ao trocar de usuário.
if "user_id" not in st.session_state:
    st.session_state.user_id = None

#Somente para fazer um teste sem depender da chave de acesso.
teste = True

#Cria um banco de dados usando SQLite que será usado para armazenar as interações e um banco para usuários.
conn = sqlite3.connect("chat_de_cria.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS mensagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    role TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
);""")
conn.commit()

#Comando no SQL para criar o usuário.
def criar_usuario(username, password):
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()
        return True
    except:
        return False
    
#Comando no SQL para verificar os dados do usuário.
def verificar_login(username, password):
    cursor.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    return cursor.fetchone()

#Comando para alterar entre cadastro e login.
if st.session_state.user_id is None:
    tab_login, tab_cadastro = st.tabs(["Login", "Cadastro"])

    #Painel de cadastro de usuário.
    with tab_cadastro:

        novo_usuario = st.text_input("Novo usuário")
        nova_senha = st.text_input("Nova senha", type="password")

        if st.button("Cadastrar"):
            criado = criar_usuario(novo_usuario, nova_senha)

            if criado:
                st.success("Usuário criado! Agora faça login.")
            else:
                st.error("Esse usuário já existe.")

    #Painel de login de usuário.
    with tab_login:

        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")

        if st.button("Entrar"):

            usuario = verificar_login(username, password)

            if usuario:
                st.session_state.user_id = usuario[0]
                st.success("Login realizado!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

    if "user_id" not in st.session_state or st.session_state.user_id is None:
        st.stop()

#Salva as mensagens no DB.
def salvar_mensagem(user_id, role, content):
    cursor.execute(
        "INSERT INTO mensagens (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()

#Puxa as mensagens anteriores da conversa.
def carregar_mensagens(user_id):
    cursor.execute(
        "SELECT role, content FROM mensagens WHERE user_id = ? ORDER BY id",
        (user_id,)
    )
    return cursor.fetchall()

#Chave de acesso à IA do Google (pode ser outra IA, mas vai ser um rolê maior).
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

#Escolhendo a versão do Gemini usada.
model = genai.GenerativeModel("gemini-2.0-flash")

#Título (muito maduro) da minha págigna de IA.
st.write("### IA DE CRIA")

#Comando para criar uma lista de mensagens caso o usuário não tenha (cookies do site).
if not "lista_mensagens" in st.session_state:
    st.session_state["lista_mensagens"] = []

    #Puxa o histórico de conversas do DB.
    historico = carregar_mensagens(st.session_state.user_id)

    #Exibe todas as mensagens enviadas.
    for role, content in historico:
        st.session_state.lista_mensagens.append({
            "role": role,
            "content": content
        })

#Memória da IA.
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])

#Comando for para exibir o histórico da conversa.
for mensagem in st.session_state["lista_mensagens"]:
    role = mensagem["role"]
    content = mensagem["content"]
    st.chat_message(role).write(content)

#Variável que recebe a entrada de dados do usuário (com um textinho genérico no fundo).
mensagem_usuario = st.chat_input("Pergunte alguma coisa")

#Condição "if" para rodar à partir do momento que o usuário escrever na caixa de mensagem.
if mensagem_usuario:

    #Reescreve na tela o que o usuário digitou (com um emote genérico).
    st.chat_message("user").write(mensagem_usuario)

    #Variável que recebe a função (role) e o conteúdo (content) da mensagem digitada pelo usuário.
    mensagem = {"role":"user", "content": mensagem_usuario}

    #Adiciona na lista de mensagens a última mensagem digitada, junto com seu endereçamento.
    st.session_state["lista_mensagens"].append(mensagem)
    salvar_mensagem(st.session_state.user_id, "user", mensagem_usuario)

    if teste:
        texto_resposta = "Seu cu é meu, menor."
    else:

    #Recebe a pergunta do usuário e manda para o Gemini, mantendo uma memória da conversa.
        resposta = st.session_state.chat.send_message(mensagem_usuario)

    #Recebe a resposta do Gemini.
        if resposta.text:
            texto_resposta = resposta.text
        else:
            texto_resposta = str(resposta)

    #Escreve na tela a resposta da IA.
    st.chat_message("assistant").write(texto_resposta)

    #Variável que recebe a função (role) e o conteúdo (content) da mensagem gerada pela IA.
    mensagem_ia = {"role": "assistant", "content": texto_resposta}

    #Adiciona na lista de mensagens a última mensagem digitada, junto com seu endereçamento.
    st.session_state["lista_mensagens"].append(mensagem_ia)
    salvar_mensagem(st.session_state.user_id, "assistant", texto_resposta)


#Botão para limpar conversa.
if st.sidebar.button("Limpar conversa"):
    cursor.execute("DELETE FROM mensagens WHERE user_id = ?",
    (st.session_state.user_id,))
    conn.commit()
    st.session_state.lista_mensagens = []
    st.rerun()

#Log de conversa para debug.
if st.sidebar.button("Log do chat"):

    cursor.execute("SELECT role, content, timestamp FROM mensagens WHERE user_id = ?",
    (st.session_state.user_id,))
    dados = cursor.fetchall()

    st.write("### Log do banco")

    for linha in dados:
        st.write(linha)

#Botão de logout.
if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.rerun()
