import time
import threading
import socket

class Middleware:
    def __init__(self, nome_estacao, gerente_ip, gerente_porta, porta_app):
        self.nome_estacao = nome_estacao
        self.ativa = False
        self.gerente_ip = gerente_ip
        self.gerente_porta = gerente_porta
        self.porta_app = porta_app  # Porta do App associada a essa estação
        self.conectado = False
        self.estacao_referencia = None  # Estação ativa que será usada como referência para a árvore.

    def iniciar(self):
        """ Função principal do Middleware, aguarda ativação """
        while True:
            if not self.ativa:
                time.sleep(1)  # Aguardar ativação
            else:
                if not self.conectado:
                    self.conectar_ao_gerente()  # Conectar ao gerente ao ativar
                if self.estacao_referencia:
                    self.conectar_a_estacao()  # Conectar à estação indicada para formar a árvore
                time.sleep(1)

    def ativar(self):
        """ Ativa o middleware quando a estação for ativada """
        self.ativa = True
        print(f'Middleware {self.nome_estacao} foi ativado pelo App!')

    def conectar_ao_gerente(self):
        """ Conecta ao Gerente e envia a porta correta do App """
        try:
            gerente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            gerente_socket.connect((self.gerente_ip, self.gerente_porta))
            
            # Envia o nome da estação e a porta correta do App para o Gerente
            gerente_socket.sendall(f'Conexão {self.nome_estacao} {self.porta_app}'.encode('utf-8'))
            resposta = gerente_socket.recv(1024).decode('utf-8')
            print(f'Resposta do gerente: {resposta}')

            # Se a resposta for uma instrução de conexão a outra estação:
            if "Conexão:" in resposta:
                partes = resposta.split()
                self.estacao_referencia = (partes[1], partes[2], int(partes[3]))  # Nome, IP, Porta da estação
                print(f'{self.nome_estacao} irá se conectar à estação {self.estacao_referencia[0]}')
            else:
                # Caso seja a primeira estação, não há necessidade de conectar a outra estação.
                print(f'{self.nome_estacao} é a primeira estação ativa.')

            self.conectado = True
        except Exception as e:
            print(f'Erro ao conectar ao gerente: {e}')

    def conectar_a_estacao(self):
        """ Conecta à estação de referência, formando a árvore de encaminhamento """
        try:
            
            # Cria um socket TCP para se conectar à estação de referência
            estacao_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            estacao_socket.connect((self.estacao_referencia[1], self.estacao_referencia[2]))
            
            # Envia uma mensagem para a estação de referência informando que a conexão foi estabelecida
            estacao_socket.sendall(f'{self.nome_estacao} conectada'.encode('utf-8'))
            
            # Recebe a resposta da estação de referência
            resposta = estacao_socket.recv(1024).decode('utf-8')
            
            # Fecha o socket após a comunicação
            estacao_socket.close()
        except Exception as e:
            print(f'Erro ao conectar à estação {self.estacao_referencia[0]}: {e}')
