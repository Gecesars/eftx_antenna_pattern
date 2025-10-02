import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- 1. Configuração da API Key ---
load_dotenv()

try:
    GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except KeyError:
    print("Erro: A variável de ambiente 'GEMINI_API_KEY' não foi encontrada.")
    print("Por favor, verifique se você criou o arquivo '.env' no mesmo diretório")
    print("e se a chave 'GEMINI_API_KEY' está definida corretamente dentro dele.")
    exit()


# --- 2. Definição do "Cérebro" do Assistente (Persona) ---
system_prompt = """
Você é o 'AntennaExpert', um assistente de IA especialista, integrado a um software de
design e simulação de antenas. Sua principal função é ajudar os usuários com todos os
aspectos do design de antenas, teoria eletromagnética e o uso prático do software.

Suas respostas devem ser:
- **Técnicas e Precisas:** Use a terminologia correta (e.g., SWR, ganho, diretividade, impedância, polarização).
- **Didáticas:** Explique conceitos complexos de forma clara. Se um usuário perguntar "o que é SWR?",
  responda de forma simples e depois, se apropriado, ofereça uma explicação mais aprofundada.
- **Contextuais ao Software:** Aja como se conhecesse o software. Por exemplo, você pode dizer
  "Para visualizar o padrão de radiação 3D, vá para o menu 'Resultados' e selecione 'Visualizador 3D'".
- **Proativas:** Se um usuário descrever um problema (e.g., "minha simulação mostra lóbulos laterais altos"),
  ofereça possíveis causas e soluções.

Seus conhecimentos incluem, mas não se limitam a:
- Tipos de Antenas: Dipolos, monopólios, Yagi-Uda, patch, microstrip, antenas parabólicas, etc.
- Parâmetros de Antenas: Ganho, eficiência, largura de banda, relação frente-costas.
- Ferramentas de Análise: Smith Chart, padrões de radiação (azimute e elevação).
- Dicas de Simulação: Definição de malha (meshing), condições de contorno e fontes de excitação.

Comece a conversa se apresentando de forma breve e profissional.
"""

# --- 3. Inicialização do Modelo e do Chat ---
# Usando o modelo mais recente e rápido, 'gemini-1.5-flash-latest'.
model = genai.GenerativeModel('gemini-2.5-pro') # <-- LINHA ALTERADA

chat = model.start_chat(history=[
    {
        "role": "user",
        "parts": [system_prompt]
    },
    {
        "role": "model",
        "parts": ["Olá! Eu sou o AntennaExpert, seu assistente para design e simulação de antenas. Como posso ajudá-lo hoje?"]
    }
])


# --- 4. Loop de Interação com o Usuário ---
def main():
    """Função principal que executa o loop do chat."""
    print("✅ Assistente 'AntennaExpert' iniciado.")
    print("   Digite sua pergunta ou 'sair' para terminar a sessão.")
    print("-" * 50)
    print(f"AntennaExpert: Olá! Eu sou o AntennaExpert, seu assistente para design e simulação de antenas. Como posso ajudá-lo hoje?")

    while True:
        try:
            user_input = input("Você: ")

            if user_input.lower() == 'sair':
                print("AntennaExpert: Sessão encerrada. Até logo!")
                break

            response = chat.send_message(user_input)
            print(f"AntennaExpert: {response.text}")

        except Exception as e:
            print(f"Ocorreu um erro: {e}")
            break

if __name__ == "__main__":
    main()