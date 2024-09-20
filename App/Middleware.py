import time
import threading
import socket

class Middleware:
    def __init__(self, nome_estacao, gerente_ip, gerente_porta, porta_app, app):
        self.nome_estacao = nome_estacao
        self.ativa = False
        self.gerente_ip = gerente_ip
        self.gerente_porta = gerente_porta
        self.ip = '127.0.0.1'
        self.porta_middleware = porta_app  # Porta do App associada a essa estação
        self.conectado = False
        self.estacao_referencia = None  # Estação ativa que será usada como referência para a árvore.
        self.app = app
        self.estacao_conectada = None  # Estação conectada abaixo na árvore de encaminhamento

                
    def ativar(self):
        """ Ativa o middleware quando a estação for ativada """
        self.ativa = True
        print(f'Middleware {self.nome_estacao} foi ativado pelo App!')

        # Conecta-se ao gerente primeiro
        self.conectar_ao_gerente()

        # Aguardar até que esteja conectado
        while not self.conectado:
            time.sleep(1)


    def servidor_tcp_middleware(self):
        
        """ Configura o servidor TCP para o Middleware """
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.porta_middleware))
        servidor.listen(10)  # Configura o servidor para aceitar até 5 conexões simultâneas.

        while True:
            cliente, endereco = servidor.accept()
            # Cria uma nova thread para tratar cada conexão de cliente.
            cliente_thread = threading.Thread(target=self.lidar_com_cliente_middleware, args=(cliente,))
            cliente_thread.start()
            
            
    def lidar_com_cliente_middleware(self, cliente_socket):
        """ Lida com as mensagens recebidas via TCP no Middleware """
        while True:
            # Recebe a mensagem do cliente e decodifica para string.
            msg = cliente_socket.recv(1024).decode('utf-8')
            
            if not msg:
                break

            print(f'{self.nome_estacao} recebeu: {msg}')
            self.processar_comando(msg,cliente_socket)
        cliente_socket.close()
    
    
    def processar_comando(self, comando, cliente_socket):
        """ Processa os comandos recebidos via TCP no Middleware """
        partes = comando.strip().split()
        if not partes:
            return
        codigo = partes[0].upper()
        if codigo == "CONEXÃO":
            self.conectar_a_estacao_referencia(partes[1], partes[2], int(partes[3]))
        elif codigo == "VAGAS":
            info_vagas = self.processar_vagas()
            if info_vagas:
                resposta = str(info_vagas)
                cliente_socket.sendall(resposta.encode('utf-8'))
        
    def conectar_a_estacao_referencia(self, nome, ip, porta):
        """ Conecta a estação ativa de referência """
        self.estacao_conectada = (nome, ip, porta)
        print(f'{self.nome_estacao} conectado a {nome} na porta {porta}')
        
        
    def conectar_ao_gerente(self):
        """ Conecta ao Gerente e envia a porta correta do App """
        try:
            gerente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            gerente_socket.connect((self.gerente_ip, self.gerente_porta))
            
            # Envia o nome da estação e a porta correta do App para o Gerente
            gerente_socket.sendall(f'Conexão {self.nome_estacao} {self.porta_middleware}'.encode('utf-8'))
            resposta = gerente_socket.recv(1024).decode('utf-8')
            print(f'Resposta do gerente: {resposta}')

            # Se a resposta for uma instrução de conexão a outra estação:
            if "Conexão:" in resposta:
                partes = resposta.split()
                self.estacao_referencia = (partes[1], partes[2], int(partes[3]))  # Nome, IP, Porta da estação
                print(f'{self.nome_estacao} irá se conectar à estação {self.estacao_referencia[0]}')
                self.send_connection_request()
            else:
                # Caso seja a primeira estação, não há necessidade de conectar a outra estação.
                print(f'{self.nome_estacao} é a primeira estação ativa.')

            self.conectado = True
        except Exception as e:
            print(f'Erro ao conectar ao gerente: {e}')


    def send_connection_request(self):
        """ Envia uma solicitação de conexão à estação de referência """
        try:
            estacao_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            estacao_socket.connect((self.estacao_referencia[1], self.estacao_referencia[2]))
            estacao_socket.sendall(f'Conexão {self.nome_estacao} {self.ip} {self.porta_middleware}'.encode('utf-8'))
            print(f'{self.nome_estacao} enviou solicitação de conexão a {self.estacao_referencia[0]}')
            
        except Exception as e:
            print(f'Erro ao enviar solicitação de conexão: {e}')



    def processar_vagas(self):
        """ Processa e envia o número de vagas ocupadas e livres e propaga para outras estações """
        if not self.ativa:
            print(f'{self.nome_estacao} está inativa e não pode processar vagas.')
            return
        
        # Simula a recuperação de dados das vagas da estação.
        total_vagas = self.app.vagas_totais
        vagas_ocupadas = self.app.vagas_ocupadas
        vagas_livres = total_vagas - vagas_ocupadas

        # Inicializa a lista de informações de vagas com os dados dessa estação.
        info_vagas = [(self.nome_estacao, total_vagas, vagas_ocupadas, vagas_livres)]
        print(f'{self.nome_estacao} - Vagas ocupadas: {vagas_ocupadas}, Vagas livres: {vagas_livres}')
        
        # Conjunto de estações já processadas (para evitar duplicação)
        estacoes_processadas = {self.nome_estacao}  # Adiciona a própria estação no conjunto

        # Função interna para processar estações conectadas, evitando duplicatas
        def processar_estacao_conectada(nome_estacao, ip_estacao, porta_estacao):
            try:
                estacao_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                estacao_socket.connect((ip_estacao, porta_estacao))
                estacao_socket.sendall(f'Vagas {self.nome_estacao}'.encode('utf-8'))

                # Recebe a resposta da estação conectada abaixo e agrega o resultado
                resposta = estacao_socket.recv(1024).decode('utf-8')
                info_vagas_estacao = eval(resposta)  # Recebe a lista de tuplas com a info de vagas

                # Agrega informações de vagas apenas de estações não processadas
                for estacao in info_vagas_estacao:
                    nome = estacao[0]
                    if nome not in estacoes_processadas:
                        info_vagas.append(estacao)
                        estacoes_processadas.add(nome)

                estacao_socket.close()
            except Exception as e:
                print(f'Erro ao conectar e processar vagas da estação {nome_estacao}: {e}')
        
        # Processa a estação de referência (se existir)
        if self.estacao_referencia:
            processar_estacao_conectada(self.estacao_referencia[0], self.estacao_referencia[1], self.estacao_referencia[2])

        # Processa a estação conectada abaixo (se existir)
        if self.estacao_conectada:
            processar_estacao_conectada(self.estacao_conectada[0], self.estacao_conectada[1], self.estacao_conectada[2])

        # resposta_formatada = ', '.join([f'{nome}:{vagas_livres}-{vagas_ocupadas}' for nome, _, vagas_ocupadas, vagas_livres in info_vagas])
        
        return info_vagas
