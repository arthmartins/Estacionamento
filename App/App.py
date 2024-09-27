import threading
import time
import socket
import os
from Middleware import Middleware  # Importando a classe Middleware
import random
import re

class App:
    def __init__(self, nome, ip, porta):
        # Inicializa o App com o nome da estação, IP, porta e número de vagas totais.
        self.nome = nome
        self.ip = ip
        self.porta = porta
        self.vagas_totais = 0  # Vagas totais atribuídas a esta estação
        self.vagas_ocupadas = 0    # Inicialmente, nenhuma vaga está ocupada
        self.porta_middleware = int(f"1{porta}")

        self.middleware = Middleware(self.nome, '127.0.0.1', 8080, self.porta_middleware, porta ,self)
        self.ativa = False
        self.carros_estacionados = []
        self.lock = threading.Lock() 

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
        servidor.listen(10)  # Configura o servidor para aceitar até 5 conexões simultâneas.
        try:
            while True:
                cliente, endereco = servidor.accept()
                # Cria uma nova thread para tratar cada conexão de cliente.
                cliente_thread = threading.Thread(target=self.lidar_com_cliente, args=(cliente,))
                cliente_thread.start()
                
        except KeyboardInterrupt:
            servidor.close()

    def lidar_com_cliente(self, cliente_socket):
        """ Função para tratar as mensagens recebidas via TCP """
        while True:
            # Recebe a mensagem do cliente e decodifica para string.
            msg = cliente_socket.recv(1024).decode('utf-8')
            
            if not msg:
                break

            # Processa o comando recebido (ativar estação, por exemplo).
            self.processar_comando(msg, cliente_socket)

            time.sleep(2)
        # cliente_socket.close()

    def processar_comando(self, comando, cliente_socket):
        """ Função para processar os comandos recebidos via TCP """
        retries = 2
        num = 0
        partes = comando.strip().split()
        fila_de_espera = []
        comando_processado = False
        if not partes:
            return
        
        codigo = partes[0].upper()
        if codigo == "AE":
            print(f'App {self.nome} recebeu: {comando}')
            self.ativar()
            resposta = (f'Estação {self.nome} ativada com sucesso! ')
            cliente_socket.sendall(resposta.encode('utf-8'))
            comando_processado = True
        
        elif self.ativa:
            print(f'App {self.nome} recebeu: {comando}')

            if codigo == "VD":
                vagas = self.enviar_mensagem_middleware(f'Vagas {self.nome}')
                vagas = eval(vagas)
                # tem que vir na resposta todas as vagas
                resposta = ""
                for nome, total_vagas, vagas_ocupadas, vagas_livres in vagas:
                    resposta += f'{nome}: {vagas_livres}-{vagas_ocupadas}, '
                
                resposta = resposta[:-2] + '.'
                cliente_socket.sendall(resposta.encode('utf-8'))
                comando_processado = True
            
            
            elif "RV" in codigo:
                
                id_carro = codigo.split('.')[1] 
                fila_de_espera.append(id_carro)
                
                while fila_de_espera:
                   
                    # Protege a verificação e alteração de vagas com o Lock
                    if self.vagas_ocupadas < self.vagas_totais:
                        
                        fila_de_espera.pop(0)
                        self.carros_estacionados.append(id_carro)
                        self.vagas_ocupadas += 1
                        
                        msg_middleware = f'Gerente Estacionado {id_carro}'
                        _ = self.enviar_mensagem_middleware(msg_middleware) # Mensagem para registrar carro no gerente
                        
                        resposta = (f'OK')
                        cliente_socket.sendall(resposta.encode('utf-8'))
                    else:
                        # Usar a vaga de outra estação atraves do middleware
                        resposta = self.enviar_mensagem_middleware(f'Solicito {id_carro}')
                        
                        if resposta == "OK":
                            fila_de_espera.pop(0)
                            cliente_socket.sendall(resposta.encode('utf-8'))
                comando_processado = True        
                    
            elif "LV" in codigo:
                id_carro = codigo.split('.')[1]
            
                while num < retries:
                    
                    if id_carro in self.carros_estacionados:
                        self.carros_estacionados.remove(id_carro)
                        self.vagas_ocupadas -= 1
                        
                        msg_middleware = f'Gerente Saida {id_carro}'
                        _ = self.enviar_mensagem_middleware(msg_middleware)
                        
                        resposta = (f'Vaga liberada {id_carro}')
                        cliente_socket.sendall(resposta.encode('utf-8'))
                        break
                    else:
                        resposta = self.enviar_mensagem_middleware(f'Liberar {id_carro}')
                        if resposta == "CARRO NÃO ENCONTRADO":
                            num += 1
                            continue
                        
                        resposta = resposta + " " + id_carro
                        cliente_socket.sendall(resposta.encode('utf-8'))
                    comando_processado = True
                    resposta = (f'Carro não encontrado {id_carro}')
                    cliente_socket.sendall(resposta.encode('utf-8'))
                
                
            elif "FE" in codigo:
                
                self.ativa = False
                resposta = self.enviar_mensagem_middleware(f'Fechar')
                cliente_socket.sendall(resposta.encode('utf-8'))
                self.ativa = False
                comando_processado = True
            
            # MENSAGENS VINDO DO MIDDLWARE
            elif "ALOCAÇÃO" in codigo:
                self.vagas_totais = int(partes[1])
                resposta = (f'Vagas alocadas')
                cliente_socket.sendall(resposta.encode('utf-8'))
                comando_processado = True
            
            elif "ESTACIONAR" in codigo: # Estacionar carro que vem de outra estação.
                
                self.carros_estacionados.append(partes[1])
                self.vagas_ocupadas += 1
                
                msg_middleware = f'Gerente Estacionado {id_carro}'
                resposta_ger = self.enviar_mensagem_middleware(msg_middleware) # Mensagem para registrar carro no gerente
                
                resposta = (f'Estacionou')
                cliente_socket.sendall(resposta.encode('utf-8'))
                comando_processado = True
            
            elif "ESTACIONADO" in codigo: # Verificar se o carro está estacionado
                
                id_carro = partes[1]
                
                if id_carro in self.carros_estacionados:
                    resposta = (f'Saiu')
                    self.carros_estacionados.remove(id_carro)
                    self.vagas_ocupadas -= 1
                    
                    msg_middleware = f'Gerente Saida {id_carro}'
                    _ = self.enviar_mensagem_middleware(msg_middleware)
                    
                    resposta = (f'Saiu')
                    cliente_socket.sendall(resposta.encode('utf-8'))
                else:
                    resposta = (f'Não está estacionado')
                    cliente_socket.sendall(resposta.encode('utf-8'))
                    
                comando_processado = True
                
            elif "VAGAS" in codigo:
                with self.lock:
                    resposta = (f'{self.vagas_totais}-{self.vagas_ocupadas}')
                    cliente_socket.sendall(resposta.encode('utf-8'))
                    comando_processado = True
            
            elif "ATUALIZAR" in codigo:
                self.vagas_totais = int(partes[1])
                self.vagas_ocupadas = int(partes[2])
                
                carros = partes[3]
                id_carros = carros.split('.')
                
                for id_carro in id_carros:
                    self.carros_estacionados.append(id_carro)
                
                resposta = (f'Atualizado')
                cliente_socket.sendall(resposta.encode('utf-8'))
                
                comando_processado = True
        else:
            resposta = (f'Estação {self.nome} não está ativa comando perdido {comando}.')
            cliente_socket.sendall(resposta.encode('utf-8'))
            comando_processado = True
        
        while not comando_processado:
            time.sleep(1)
        
                            
    def enviar_mensagem_middleware(self, mensagem):
        """ Função genérica para enviar uma mensagem ao middleware via TCP """
        try:
            cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cliente_socket.connect((self.ip, self.porta_middleware))
            cliente_socket.sendall(mensagem.encode('utf-8'))
            
            resposta = cliente_socket.recv(1024).decode('utf-8')
            
            return resposta

        except socket.error as e:
            print(f"Erro ao se conectar ao middleware: {e}")
            time.sleep(2)
            return None
        # finally:
        #     cliente_socket.close()

    
    def ativar(self):
        
        self.ativa = True
        
        resposta = self.enviar_mensagem_middleware("Ativar")
        
        
        while not resposta:
            time.sleep(1)
            

# def distribuir_vagas_aleatoriamente(total_vagas, num_estacoes):
#     """ Função para distribuir as vagas aleatoriamente entre as estações """
#     vagas_por_estacao = [0] * num_estacoes
    
#     # Distribui aleatoriamente o total de vagas entre as estações.
#     for _ in range(total_vagas):
#         estacao_escolhida = random.randint(0, num_estacoes - 1)
#         vagas_por_estacao[estacao_escolhida] += 1
        
#     return vagas_por_estacao

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
    # vagas_por_estacao = distribuir_vagas_aleatoriamente(total_vagas, num_estacoes)

    # Para cada linha do arquivo, cria uma nova instância de `App` com os dados da estação.
    for i, linha in enumerate(linhas_estacoes):
        dados_estacao = linha.strip().split()
        if len(dados_estacao) == 3:
            nome, ip, porta = dados_estacao
            # vagas = vagas_por_estacao[i]
            app = App(nome, ip, int(porta))
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

