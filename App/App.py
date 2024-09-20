import threading
import time
import socket
import os
from Middleware import Middleware  # Importando a classe Middleware
import random

class App:
    def __init__(self, nome, ip, porta, vagas):
        # Inicializa o App com o nome da estação, IP, porta e número de vagas totais.
        self.nome = nome
        self.ip = ip
        self.porta = porta
        self.vagas_totais = vagas  # Vagas totais atribuídas a esta estação
        self.vagas_ocupadas = 0    # Inicialmente, nenhuma vaga está ocupada
        porta_middleware = int(f"1{porta}")
        # Cada App tem seu próprio Middleware, configurado com o endereço do gerente.
        self.middleware = Middleware(self.nome, '127.0.0.1', 8080, porta_middleware, self)
        self.ativa = False

    def iniciar(self):
        # Inicia o middleware em uma thread separada para comunicação com o gerente.
        middleware_thread = threading.Thread(target=self.middleware.servidor_tcp_middleware)
        middleware_thread.start()
        
        # Inicia o servidor TCP em outra thread para receber comandos via TCP.
        server_thread = threading.Thread(target=self.servidor_tcp)
        server_thread.start()

    def servidor_tcp(self):
        # Configura o servidor TCP que escuta na porta especificada.
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.porta))
        servidor.listen(5)  # Configura o servidor para aceitar até 5 conexões simultâneas.

        while True:
            cliente, endereco = servidor.accept()
            # Cria uma nova thread para tratar cada conexão de cliente.
            cliente_thread = threading.Thread(target=self.lidar_com_cliente, args=(cliente,))
            cliente_thread.start()

    def lidar_com_cliente(self, cliente_socket):
        """ Função para tratar as mensagens recebidas via TCP """
        while True:
            # Recebe a mensagem do cliente e decodifica para string.
            msg = cliente_socket.recv(1024).decode('utf-8')
            
            if not msg:
                break

            print(f'{self.nome} recebeu: {msg}')
            # Processa o comando recebido (ativar estação, por exemplo).
            self.processar_comando(msg, cliente_socket)

            time.sleep(2)
        cliente_socket.close()

    def processar_comando(self, comando, cliente_socket):
        """ Função para processar os comandos recebidos via TCP """
        partes = comando.strip().split()
        if not partes:
            return
        
        codigo = partes[0].upper()

        if codigo == "AE":
            self.ativar()
            resposta = (f'Estação {self.nome} ativada com sucesso! ')
            cliente_socket.sendall(resposta.encode('utf-8'))
        
        if codigo == "VD":
            vagas = self.middleware.processar_vagas()
            # tem que vir na resposta todas as vagas
            resposta = (f'Estação {vagas}')
            cliente_socket.sendall(resposta.encode('utf-8'))
        
    def ativar(self):
        # Ativa a estação e imprime as vagas disponíveis e ocupadas.
        self.ativa = True
        
        print(f'{self.nome} foi ativado! Vagas Totais: {self.vagas_totais}, Vagas Ocupadas: {self.vagas_ocupadas}')
        self.middleware.ativar()
        
        while not self.middleware.conectado:
            time.sleep(1)
            

def distribuir_vagas_aleatoriamente(total_vagas, num_estacoes):
    """ Função para distribuir as vagas aleatoriamente entre as estações """
    vagas_por_estacao = [0] * num_estacoes
    
    # Distribui aleatoriamente o total de vagas entre as estações.
    for _ in range(total_vagas):
        estacao_escolhida = random.randint(0, num_estacoes - 1)
        vagas_por_estacao[estacao_escolhida] += 1
        
    return vagas_por_estacao

def carregar_estacoes(arquivo, total_vagas):
    """ Função para carregar as estações a partir de um arquivo e distribuir vagas """
    estacoes = []
    
    # Verifica se o arquivo existe.
    if not os.path.exists(arquivo):
        print(f"Arquivo não encontrado: {arquivo}")
        return estacoes

    # Lê o arquivo que contém os dados das estações.
    with open(arquivo, 'r') as file:
        linhas_estacoes = file.readlines()
    
    num_estacoes = len(linhas_estacoes)
    # Distribui as vagas entre as estações.
    vagas_por_estacao = distribuir_vagas_aleatoriamente(total_vagas, num_estacoes)

    # Para cada linha do arquivo, cria uma nova instância de `App` com os dados da estação.
    for i, linha in enumerate(linhas_estacoes):
        dados_estacao = linha.strip().split()
        if len(dados_estacao) == 3:
            nome, ip, porta = dados_estacao
            vagas = vagas_por_estacao[i]
            app = App(nome, ip, int(porta), vagas)
            estacoes.append(app)

    return estacoes

def main():
    # Define o número total de vagas para todas as estações.
    total_vagas = 100  
    caminho_arquivo = 'file.txt' 
    
    # Carrega as estações a partir do arquivo e distribui as vagas.
    estacoes = carregar_estacoes(caminho_arquivo, total_vagas)
    
    # Inicia todas as estações em threads separadas.
    threads = []
    for estacao in estacoes:
        t = threading.Thread(target=estacao.iniciar)
        threads.append(t)
        t.start()

    # Aguarda que todas as threads terminem.
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()

