#Bibliotecas usadas no sistema.
import streamlit as st
import google.generativeai as genai
import sqlite3

#Limpar conversa ao trocar de usuário.
if "user_id" not in st.session_state:
    st.session_state.user_id = None

#Somente para fazer um teste sem depender da chave de acesso.
teste = False

#Cria um banco de dados usando SQLite que será usado para armazenar as interações e um banco para usuários.
conn = sqlite3.connect("chat_de_cria.db", check_same_thread=False)
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
    
#Consulta no SQL para verificar os dados do usuário.
def verificar_login(username, password):
    cursor.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    return cursor.fetchone()

#Botão para alterar entre cadastro e login.
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
                st.error("Usuário ou senha inválidos.")

    if "user_id" not in st.session_state or st.session_state.user_id is None:
        st.stop()

#Consulta de SQL para salvar as mensagens no DB.
def salvar_mensagem(user_id, role, content):
    cursor.execute(
        "INSERT INTO mensagens (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()

#Consulta de SQL para puxar as mensagens anteriores da conversa.
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

#Comando para criar uma lista de mensagens caso o usuário não tenha, tipo um "cookie do site".
if not "lista_mensagens" in st.session_state:
    st.session_state["lista_mensagens"] = []

    #Puxa o histórico de conversas do DB.
    historico = carregar_mensagens(st.session_state.user_id)

    #Exibe as últimas mensagens enviadas.
    for role, content in historico:
        st.session_state.lista_mensagens.append({
            "role": role,
            "content": content
        })

#Comando for para exibir o histórico da conversa.
for mensagem in st.session_state["lista_mensagens"]:
    role = mensagem["role"]
    content = mensagem["content"]
    st.chat_message(role).write(content)

#Variável que recebe a entrada de dados do usuário (com um textinho genérico no fundo).
mensagem_usuario = st.chat_input("Pergunte alguma coisa")

#Condição "if" para rodar à partir do momento que o usuário escrever na caixa de mensagem.
if mensagem_usuario:

    # Mostra mensagem do usuário e a salva no DB.
    st.chat_message("user").write(mensagem_usuario)
    mensagem = {"role": "user", "content": mensagem_usuario}
    st.session_state.lista_mensagens.append(mensagem)
    salvar_mensagem(st.session_state.user_id, "user", mensagem_usuario)

    # Limita histórico para evitar estouro de tokens (spoiler: estoura do mesmo jeito).
    historico = st.session_state.lista_mensagens[-10:]

    historico_texto = ""
    for msg in historico:
        historico_texto += f"{msg['role']}: {msg['content']}\n"
    prompt = historico_texto + f"user: {mensagem_usuario}"

    # Spinner para evitar impressão de travamento
    with st.spinner("Pensando..."):
        try:
            if teste: #Era um teste bobo, mas ficou no código e fé.
                texto_resposta = "Seu cu é meu, menor."
            else:
                resposta = model.generate_content(prompt)

                #Armazena a resposta vinda da IA na variável que será impressa.
                if hasattr(resposta, "text") and resposta.text:
                    texto_resposta = resposta.text
                else:
                    texto_resposta = str(resposta)

        #Texto com ModelException caso aconteça algum envio de dados grotesco (raro, mas acontece sempre).
        except Exception:
            texto_resposta = "A IA está sobrecarregada agora. Tente novamente em alguns segundos."

    # Mostra resposta da IA na tela e salva no DB.
    st.chat_message("assistant").write(texto_resposta)
    mensagem_ia = {"role": "assistant", "content": texto_resposta}
    st.session_state.lista_mensagens.append(mensagem_ia)
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
