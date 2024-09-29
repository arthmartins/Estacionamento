import time
import threading
import socket
import re

PING_INTERVAL = 1
TIMEOUT_INTERVAL = 5

class Middleware:
    def __init__(self, nome_estacao, gerente_ip, gerente_porta, porta_middleware,porta_app , app):
        self.nome_estacao = nome_estacao
        self.ativa = False
        self.gerente_ip = gerente_ip
        self.gerente_porta = gerente_porta
        self.ip = '127.0.0.1'
        self.porta_middleware = porta_middleware
        self.porta_app = porta_app # Porta do App associada a essa estação
        self.conectado = False
        self.estacao_referencia = None  # Estação ativa que será usada como referência para a árvore.
        self.app = app
        self.estacao_conectada = None  # Estação conectada abaixo na árvore de encaminhamento
        self.ultima_vez_heartbeat_referencia = time.time()  # Tempo do último ping recebido da estação de referência
        self.ultima_vez_heartbeat_conectada = time.time()   # Tempo do último ping recebido da estação conectada
        self.lock = threading.Lock()
                
    def ativar(self):
        """ Ativa o middleware quando a estação for ativada """
        self.ativa = True

        # Conecta-se ao gerente primeiro
        resposta = self.conectar_ao_gerente()

        # Aguardar até que esteja conectado
        while not resposta:
            time.sleep(1)
        
        # Thread para o envio contínuo de pings via TCP
        threading.Thread(target=self.heartbeat, daemon=True).start()
        # Thread para monitorar os heartbeats
        threading.Thread(target=self.monitor_heartbeat, daemon=True).start()

        return "Estação ativada com sucesso!"

    def servidor_tcp_middleware(self):
        
        """ Configura o servidor TCP para o Middleware """
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.porta_middleware))
        servidor.listen(10)  # Configura o servidor para aceitar até 5 conexões simultâneas.
        try:
            while True:
                cliente, endereco = servidor.accept()
                with self.lock:
                    cliente_thread = threading.Thread(target=self.lidar_com_cliente_middleware, args=(cliente,))
                    cliente_thread.start()
                
        except KeyboardInterrupt:
            servidor.close()
            print("Servidor encerrado.")
            
            
    def lidar_com_cliente_middleware(self, cliente_socket):
        """ Lida com as mensagens recebidas via TCP no Middleware """
        try:
            while True:
                # Recebe a mensagem do cliente e decodifica para string.
                msg = cliente_socket.recv(1024).decode('utf-8')
                
                if not msg:
                    break
                
                self.processar_comando(msg, cliente_socket)
        except ConnectionResetError:
            print(f'Conexão resetada pelo cliente: {cliente_socket.getpeername()}')
        finally:
            cliente_socket.close()
    
    
    def processar_comando(self, comando, cliente_socket):
        """ Processa os comandos recebidos via TCP no Middleware """
        partes = comando.strip().split()
        if not partes:
            return
        codigo = partes[0].upper()
        if codigo == "ATIVAR":

            resposta = self.ativar()
            cliente_socket.sendall(resposta.encode('utf-8'))
        
        elif self.ativa:
            
            if codigo == "CONEXÃO":
                self.conectar_a_estacao_referencia(partes[1], partes[2], int(partes[3]))
                resposta = "Conexão estabelecida"
                cliente_socket.sendall(resposta.encode('utf-8'))
                
            elif codigo == "CONECTE":
                self.conectar_a_estacao_conectada(partes[1], partes[2], int(partes[3]))
                resposta = "Conexão estabelecida"
                cliente_socket.sendall(resposta.encode('utf-8'))
                
            
            elif codigo == "ALOCAÇÃO":
                resposta = self.enviar_mensagem_app(f'ALOCAÇÃO {partes[1]}')
            
            elif codigo == "VAGAS":
                print(f"Processando vagas para {partes[1]}")
                origem = partes[1]
                estacoes_processadas = {origem} 
                info_vagas = self.processar_vagas(origem, estacoes_processadas)
                if info_vagas:
                    resposta = str(info_vagas)
                    cliente_socket.sendall(resposta.encode('utf-8'))

                    
            elif codigo == "SOLICITO":
                print(f"Requisição de vaga para {partes[1]}")
                id_carro = partes[1]
                origem = partes[2] if len(partes) > 2 else self.nome_estacao  # Define a origem da solicitação
                resposta = self.requisitar_vaga(id_carro, origem)
                cliente_socket.sendall(resposta.encode('utf-8'))
            
            elif codigo == "LIBERAR":
                id_carro = partes[1]
                resposta = self.liberar_vaga(id_carro)
                cliente_socket.sendall(resposta.encode('utf-8'))
            
            elif codigo == "FECHAR":
                self.ativa = False
                resposta = (f'{self.nome_estacao} desativada')
                cliente_socket.sendall(resposta.encode('utf-8'))
            
            elif codigo == "PING":
                print(f"Recebido ping de {partes[1]}")
                self.lidar_ping(partes[1])
                
            elif codigo == "TROCAR":
                
                if partes[1] == "conexão":
                    if partes[2] == "None":
                        self.estacao_conectada = None
                    else:
                        match = re.search(r"\(([^)]+)\)", comando)
                        if match:
                            # Separando os elementos para criar a tupla
                            elementos = match.group(1).replace("'", "").split(", ")
                            estacao_conectada = (elementos[0], elementos[1], int(elementos[2]))
                            
                        self.estacao_conectada = estacao_conectada
                    
                elif partes[1] == "referência":
                    if partes[2] == "None":
                        self.estacao_referencia = None
                    else:
                    
                        match = re.search(r"\(([^)]+)\)", comando)
                        if match:
                            # Separando os elementos para criar a tupla
                            elementos = match.group(1).replace("'", "").split(", ")
                            estacao_conectada = (elementos[0], elementos[1], int(elementos[2]))
                            
                        self.estacao_referencia = estacao_conectada
                            
            elif codigo == "ELEICAO":
                print(f"Processando eleiicao para {self.nome_estacao}")
                origem = partes[1]
                estacoes_processadas = {origem}
            
                info_vagas = self.processar_eleicao(origem, estacoes_processadas)
                if info_vagas:
                    resposta = str(info_vagas)
                    cliente_socket.sendall(resposta.encode('utf-8'))
                
            elif codigo == "GERENTE":
                if partes[1] == "Estacionado":
                    resposta = self.enviar_mensagem_gerente(f'Estacionado {self.nome_estacao} {partes[2]}')
                    cliente_socket.sendall(resposta.encode('utf-8'))
                    
                elif partes[1] == "Saida":
                    resposta = self.enviar_mensagem_gerente(f'Saida {self.nome_estacao} {partes[2]}')
                    cliente_socket.sendall(resposta.encode('utf-8'))
                
                elif partes[1] == "Alocação":
                    
                    resposta = self.enviar_mensagem_app(f'Atualizar {partes[2]} {partes[3]} {partes[4]}')
                    cliente_socket.sendall(resposta.encode('utf-8'))
    
    def enviar_mensagem_app(self, mensagem):
        """ Função genérica para enviar uma mensagem ao App via TCP """
        try: 
            cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cliente_socket.connect((self.ip, self.porta_app))
            cliente_socket.sendall(mensagem.encode('utf-8'))

            resposta = cliente_socket.recv(1024).decode('utf-8')
            
            return resposta

        except socket.error as e:
            print(f"Erro ao se conectar ao middleware: {e}")
            time.sleep(2)
        # finally:
        #     cliente_socket.close()
        
    def enviar_mensagem_gerente(self, mensagem):
        """ Função genérica para enviar uma mensagem ao Gerente via TCP """
        try:
            cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cliente_socket.connect((self.gerente_ip, self.gerente_porta))
            cliente_socket.sendall(mensagem.encode('utf-8'))
            
            resposta = cliente_socket.recv(1024).decode('utf-8')
            
            return resposta

        except socket.error as e:
            print(f"Erro ao se conectar ao gerente: {e}")
            return None
        # finally:
        #     cliente_socket.close()
    
    def enviar_mensagem_middleware(self, ip, porta, mensagem):
        """ Função genérica para enviar uma mensagem a outro Middleware via TCP """
        try:
            cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cliente_socket.settimeout(10)
            cliente_socket.connect((ip, porta))
            cliente_socket.sendall(mensagem.encode('utf-8'))
            
            resposta = cliente_socket.recv(1024).decode('utf-8')
            #cliente_socket.close()
            
            return resposta

        except socket.error as e:
            print(f"Erro ao se conectar ao middleware: {e}")
            return None
        # finally:
        #     cliente_socket.close()
        
    
    def conectar_a_estacao_referencia(self, nome, ip, porta):
        """ Conecta a estação ativa de referência """
        self.estacao_referencia = (nome, ip, porta)
        print(f'{self.nome_estacao} referecia a {nome} na porta {porta}')
        _ = self.enviar_mensagem_middleware(ip, porta, f'Conecte {self.nome_estacao} {self.ip} {self.porta_middleware}')
    
    def conectar_a_estacao_conectada(self, nome, ip, porta):
        """ Conecta a estação ativa conectada """
        self.estacao_conectada = (nome, ip, porta)
        print(f'{self.nome_estacao} conectado a {nome} na porta {porta}')
        
        
        
    def conectar_ao_gerente(self):
        """ Conecta ao Gerente e envia a porta correta do App """
        try:
            # gerente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # gerente_socket.connect((self.gerente_ip, self.gerente_porta))
            
            mensagem = f'Conexão {self.nome_estacao} {self.porta_middleware}'
            resposta = self.enviar_mensagem_gerente(mensagem)
            
            self.conectado = True
            return True
        except Exception as e:
            print(f'Erro ao conectar ao gerente: {e}')


    def processar_vagas(self, origem=None, estacoes_processadas=None):
        """ Processa e envia o número de vagas ocupadas e livres e propaga para todas as estações na fila circular """

        # Define a origem da solicitação, se não for fornecida
        if origem is None:
            origem = self.nome_estacao


        if estacoes_processadas is None:
            estacoes_processadas = {self.nome_estacao}  # Inicializa o conjunto se não for fornecido

        # Simula a recuperação de dados das vagas da estação atual.
        vagas_estacao = self.enviar_mensagem_app("VAGAS")
        vagas_estacao = vagas_estacao.split("-")
        total_vagas = int(vagas_estacao[0])
        vagas_ocupadas = int(vagas_estacao[1])
        vagas_livres = total_vagas - vagas_ocupadas

        # Inicializa a lista de informações de vagas com os dados dessa estação.
        info_vagas = [(self.nome_estacao, total_vagas, vagas_ocupadas, vagas_livres)]
        
        # Adiciona a estação atual ao conjunto de processadas
        estacoes_processadas.add(self.nome_estacao)

        # Inicia o processamento a partir da estação de referência
        estacao_atual = self.estacao_referencia

        # Percorre a fila circular até retornar à estação original
        while estacao_atual and estacao_atual[0] != origem:
            nome_estacao = estacao_atual[0]
            ip_estacao = estacao_atual[1]
            porta_estacao = estacao_atual[2]

            if nome_estacao in estacoes_processadas:
                # Se já foi processada, interrompe o loop para evitar redundância
                break
            
            try:
                # Envia mensagem para a estação de referência solicitando as vagas
                mensagem = f'Vagas {origem}'
                resposta = self.enviar_mensagem_middleware(ip_estacao, porta_estacao, mensagem)

                info_vagas_estacao = eval(resposta)  # Recebe a lista de tuplas com a info de vagas
                
                # Agrega informações de vagas apenas de estações não processadas
                for estacao in info_vagas_estacao:
                    nome = estacao[0]
                    if nome not in estacoes_processadas:
                        info_vagas.append(estacao)
                        estacoes_processadas.add(nome)
                
                estacao_atual = (info_vagas_estacao[-1][0], ip_estacao, porta_estacao)

            except Exception as e:
                print(f'Erro ao conectar e processar vagas da estação {nome_estacao}: {e}')
                break
        
        return info_vagas




    def requisitar_vaga(self, id_carro, origem=None):
        """ Requisita uma vaga disponível na estação atual ou em outras estações """
        # Define a origem da solicitação, se não for fornecida
        if origem is None:
            origem = self.nome_estacao

        # Se a origem for a estação atual, para a propagação
        if origem == self.nome_estacao:
            return "SEM VAGAS"

        # Verifica a própria estação primeiro
        vagas_estacao = self.enviar_mensagem_app("VAGAS")
        vagas_estacao = vagas_estacao.split("-")
        total_vagas = int(vagas_estacao[0])
        vagas_ocupadas = int(vagas_estacao[1])
        vagas_livres = total_vagas - vagas_ocupadas
        
        # Se houver uma vaga livre, a preenche e retorna "OK"
        if vagas_livres > 0:
            resposta = self.enviar_mensagem_app(f'Estacionar {id_carro}')
            print(f'{self.nome_estacao} - Vaga alocada.')
            return "OK"

        # Se não houver vaga na própria estação, propaga a solicitação para a estação de referência na fila circular
        estacoes_processadas = {self.nome_estacao}  # Adiciona a própria estação no conjunto

        estacao_atual = self.estacao_referencia

        # Percorre a fila circular até retornar à estação original
        while estacao_atual and estacao_atual[0] != origem:
            nome_estacao = estacao_atual[0]
            ip_estacao = estacao_atual[1]
            porta_estacao = estacao_atual[2]

            if nome_estacao in estacoes_processadas:
                # Se já foi processada, interrompe o loop para evitar redundância
                break
            
            try:
                # Envia mensagem para a estação de referência solicitando vaga
                mensagem = f'SOLICITO {id_carro}'
                resposta = self.enviar_mensagem_middleware(ip_estacao, porta_estacao, mensagem)
                
                if resposta == "OK":
                    print(f'Vaga alocada na estação {nome_estacao}.')
                    return "OK"
                
                # Marca a estação como processada
                estacoes_processadas.add(nome_estacao)

                # Atualiza para a próxima estação na fila circular
                estacao_atual = self.estacao_referencia

            except Exception as e:
                print(f'Erro ao conectar e requisitar vaga da estação {nome_estacao}: {e}')
                break

        # Se nenhuma vaga foi encontrada
        return "SEM VAGAS"

    
    
    def liberar_vaga(self, id_carro):
        """ Libera a vaga associada ao carro 'id_carro' na estação atual ou em outras estações conectadas """
        
        estacoes_processadas = {self.nome_estacao}  # Adiciona a própria estação ao conjunto de estações processadas

        # Função interna para requisitar a liberação de vaga em outra estação
        def liberar_em_estacao_conectada(nome_estacao, ip_estacao, porta_estacao):
            # Evita processar a mesma estação mais de uma vez
            if nome_estacao in estacoes_processadas:
                return None
            
            estacoes_processadas.add(nome_estacao)  # Marca a estação como processada

            try:
                mensagem = f'LIBERAR {id_carro}'
                resposta = self.enviar_mensagem_middleware(ip_estacao, porta_estacao, mensagem)
        
                if resposta == "Vaga liberada":
                    return f'Vaga liberada'
            except Exception as e:
                print(f'Erro ao conectar e liberar vaga da estação {nome_estacao}: {e}')

            return None

        # Primeiro, tenta liberar a vaga na própria estação
        resposta = self.enviar_mensagem_app(f'ESTACIONADO {id_carro}')
        if resposta == "Saiu":
            return f'Vaga liberada'

        # Verifica a estação de referência (se existir e ainda não foi processada)
        if self.estacao_referencia is not None and self.estacao_referencia[0] not in estacoes_processadas:
            resposta = liberar_em_estacao_conectada(self.estacao_referencia[0], self.estacao_referencia[1], self.estacao_referencia[2])
            if resposta == "Vaga liberada":
                return resposta

        # Se o carro não foi encontrado em nenhuma estação
        return "CARRO NÃO ENCONTRADO"



    def send_ping(self, station_address):
        """Envia um ping para uma estação específica via TCP."""
        try:
            station_address_ip_porta = (station_address[1], station_address[2])
            message = f"ping {self.nome_estacao}".encode('utf-8')  # Formato da mensagem com nome da estação

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(station_address_ip_porta)  # Conecta ao IP e porta da estação
                
                s.sendall(message)  # Envia a mensagem
                
        except Exception as e:
            print(f"Erro ao enviar ping para {station_address_ip_porta}: {e}")


    def lidar_ping(self, station_name):
        """Lida com a conexão TCP recebida e processa o ping."""
        try:            
            # if self.estacao_referencia is not None:
            #     if station_name == self.estacao_referencia[0]:
            #         self.ultima_vez_heartbeat_referencia = time.time()
                    
            if self.estacao_conectada is not None:
                if station_name == self.estacao_conectada[0]:
                    self.ultima_vez_heartbeat_conectada = time.time()
            
        except Exception as e:
            print(f"Erro ao lidar com cliente: {e}")


    def monitor_heartbeat(self):
        """Monitora se as estações conectadas ou referenciadas continuam enviando pings."""
        while self.ativa:
            agora = time.time()

            # Verifica se a estação de referência parou de enviar pings
            # if self.estacao_referencia is not None and agora - self.ultima_vez_heartbeat_referencia > TIMEOUT_INTERVAL:
            #     print(f"{self.nome_estacao} detectou que a estação de referência {self.estacao_referencia[0]} está offline.")
            #     self.detectar_falha(self.estacao_referencia[0])

            if self.estacao_conectada is not None and agora - self.ultima_vez_heartbeat_conectada > TIMEOUT_INTERVAL:
                print(f"{self.nome_estacao} detectou que a estação conectada {self.estacao_conectada[0]} está offline.")
                
                self.detectar_falha(self.estacao_conectada[0])
                
            time.sleep(PING_INTERVAL) 
                
    def heartbeat(self):
        """Controla o envio de pings para as estações conectadas e referenciadas via TCP."""
        while self.ativa:
            if self.estacao_referencia is not None:
                self.send_ping(self.estacao_referencia)
            
            time.sleep(PING_INTERVAL)  # Espera antes de enviar o próximo ping



    def detectar_falha(self, estacao_nome):
        """Inicia o processo de eleição ao detectar que uma estação está offline."""
        print(f"{self.nome_estacao} detectou que a estação {estacao_nome} está offline. Iniciando processo de eleição...")
        resposta = self.enviar_mensagem_gerente(f"Desativar {estacao_nome}")
        print(f"Resposta do gerente: {resposta}")
        while not resposta:
            time.sleep(1)
        
        partes = resposta.split()
                
        vagas = int(partes[0])
        vagas_ocupadas = int(partes[1])
        carros_estacionados = partes[2:]
        limpos = [id.strip("[]',") for id in carros_estacionados]

        resultado = '.'.join(limpos)
        carros_estacionados = resultado
        if carros_estacionados == '':
            carros_estacionados = 'None'
        
        lista_vagas = self.enviar_mensagem_middleware(self.estacao_referencia[1], self.estacao_referencia[2], f'Eleicao {self.estacao_referencia[0]}')
        lider, vagas_livres = self.encontrar_estacao_com_menos_vagas(lista_vagas)
        
        self.assumir_vagas(lider, vagas, vagas_ocupadas, carros_estacionados)


    def encontrar_estacao_com_menos_vagas(self, lista_vagas):
        """ Processa a lista de vagas e encontra a estação com o menor número de vagas livres """
        
        # Converte a string recebida em uma lista de tuplas
        try:
            vagas_info = eval(lista_vagas)
        except Exception as e:
            print(f"Erro ao processar a lista de vagas: {e}")
            return None

        estacao_menor_vaga = min(vagas_info, key=lambda x: x[1])
        
        nome_estacao = estacao_menor_vaga[0]
        vagas_livres = estacao_menor_vaga[1]

        print(f"Estação {nome_estacao} possui o menor número de vagas livres: {vagas_livres}")

        return nome_estacao, vagas_livres
    

    def processar_eleicao(self, origem=None, estacoes_processadas=None):
        """ Processa e envia o número de vagas livres para todas as estações na fila circular """

        # Define a origem da solicitação, se não for fornecida
        if origem is None:
            origem = self.nome_estacao

        # Inicializa o conjunto de estações processadas, se não fornecido
        if estacoes_processadas is None:
            estacoes_processadas = {self.nome_estacao}

        # Simula a recuperação de dados das vagas da estação atual.
        vagas_estacao = self.enviar_mensagem_app("VAGAS")
        vagas_estacao = vagas_estacao.split("-")
        total_vagas = int(vagas_estacao[0])
        vagas_ocupadas = int(vagas_estacao[1])
        vagas_livres = total_vagas - vagas_ocupadas

        # Inicializa a lista de informações de vagas livres com os dados dessa estação.
        vagas_info = [(self.nome_estacao, vagas_livres)]

        # Adiciona a estação atual ao conjunto de processadas
        estacoes_processadas.add(self.nome_estacao)

        # Inicia o processamento a partir da estação de referência
        estacao_atual = self.estacao_referencia

        # Percorre a fila circular até retornar à estação original
        while estacao_atual and estacao_atual[0] != origem:
            nome_estacao = estacao_atual[0]
            ip_estacao = estacao_atual[1]
            porta_estacao = estacao_atual[2]

            if nome_estacao in estacoes_processadas:
                # Se já foi processada, interrompe o loop para evitar redundância
                break

            try:
                # Envia mensagem para a estação de referência solicitando as vagas
                mensagem = f'Eleicao {origem}'
                resposta = self.enviar_mensagem_middleware(ip_estacao, porta_estacao, mensagem)

                # Recebe a lista de tuplas com a info de vagas e converte
                info_vagas_estacao = eval(resposta)
                
                # Adiciona informações de vagas livres da estação não processada
                for estacao in info_vagas_estacao:
                    nome = estacao[0]
                    vagas_livres_estacao = int(estacao[1])  # Index 3 corresponde ao número de vagas livres
                    if nome not in estacoes_processadas:
                        vagas_info.append((nome, vagas_livres_estacao))
                        estacoes_processadas.add(nome)

                # Atualiza a estação atual para a próxima na fila circular
                estacao_atual = (info_vagas_estacao[-1][0], ip_estacao, porta_estacao)

            except Exception as e:
                print(f'Erro ao conectar e processar vagas da estação {nome_estacao}: {e}')
                break

        return vagas_info


    
    # def assumir_vagas(self, lider, vagas, vagas_ocupadas,carros_estacionados):
    def assumir_vagas(self, lider, vagas, vagas_ocupadas, carros_estacionados):
        """Assume as vagas da estação que saiu ou ficou offline."""
        print(f"{lider} está assumindo as vagas da estação.")
        self.enviar_mensagem_gerente(f"Eleição {lider} {vagas} {vagas_ocupadas} {carros_estacionados}")
        pass