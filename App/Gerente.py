import socket
import threading
import random
import re

class Gerente:
    def __init__(self, ip, porta):
        self.ip = ip
        self.porta = porta
        self.vagas_estacionamento = 5
        self.estacoes_ativas = {}
        
        self.estacao_vagas = {} 
        self.conexoes = {}
        self.vagas_ocupadas = {}
        self.id_carros = {}
        
        self.estacao_index = 0  # Índice para garantir balanceamento das conexões

    def iniciar(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.porta))
        servidor.listen(10)

        while True:
            cliente, endereco = servidor.accept()
            print(f'Conexão recebida de {endereco}')
            cliente_thread = threading.Thread(target=self.lidar_com_cliente, args=(cliente,))
            cliente_thread.start()


    def lidar_com_cliente(self, cliente_socket):
        """ Lida com a conexão de uma estação """
        msg = cliente_socket.recv(1024).decode('utf-8')
        
        if msg:
            
            print(f'Gerente recebeu: {msg}')
            partes = msg.split()

            if partes[0] == "Conexão":
                nome_estacao = partes[1]
                porta_estacao = int(partes[2])  # Recebe a porta correta do App
                ip_estacao = cliente_socket.getpeername()[0]

                # Registra a nova estação com a porta correta
                self.registrar_estacao(nome_estacao, ip_estacao, porta_estacao)
                
                self.distribuir_vagas()
                
                self.informar_vagas_estacoes()

                self.atualizar_referencias_circular()
              
                cliente_socket.sendall('Estação registrada com sucesso'.encode('utf-8'))
                    
           
            if partes[0] == "Desativar":
        
                nome_estacao = partes[1]
                if nome_estacao in self.estacoes_ativas:
                    
                    vagas = self.estacao_vagas.get(nome_estacao, 0)
                    vagas_ocupadas = self.vagas_ocupadas.get(nome_estacao, 0)
                    
                    carros = []
                    carros = self.id_carros.get(nome_estacao, [])
                    
                    estacao_referencia_info = self.conexoes.get(nome_estacao)

                    if estacao_referencia_info is not None:
                        estacao_referencia = estacao_referencia_info[0]  # Extraindo apenas o nome da estação
                        
                    else:
                        estacao_referencia = None
                        
                    estacao_conectada = self.encontrar_estacao_x(nome_estacao)
                    
                    if estacao_conectada in self.conexoes:
                        del self.conexoes[estacao_conectada]
                    
                    if estacao_referencia is not None:
                        
                        # Estação completa se refere ao ip e a porta
                        estacao_completa = self.estacoes_ativas.get(estacao_conectada)
                        estacao_completa_formatada = (estacao_conectada,) + estacao_completa
                        
                        self.enviar_mensagem_estacao(estacao_referencia, f"Trocar conexão {estacao_completa_formatada}")
                    
                    
                        estacao_completa = self.estacoes_ativas.get(estacao_referencia)
                        estacao_completa_formatada = (estacao_referencia,) + estacao_completa
                        
                        print(f'Estação {estacao_completa_formatada}.')
                        self.enviar_mensagem_estacao(estacao_conectada, f"Trocar referência {estacao_completa_formatada}")
                        self.conexoes[estacao_conectada] = estacao_referencia
                    
                    else:
                        print(f'Só essa estação estava ativa.')

                    # Deletar conexão da estação morta
                    if nome_estacao in self.conexoes:
                        del self.conexoes[nome_estacao]
                                      
                    # Deletar a estação morta das estções ativas
                    del self.estacoes_ativas[nome_estacao]
                    print(f'GERENTE {nome_estacao} desativada.')
                    
                    # Deletando o dicinário de carros da estaçao morta
                    if nome_estacao in self.id_carros:
                        del self.id_carros[nome_estacao]
                    
                    # Deletando o dicinário de vagas ocupadas da estaçao morta
                    del self.vagas_ocupadas[nome_estacao]
                    
                    mensagem = f'{vagas} {vagas_ocupadas} {carros}'
                    cliente_socket.sendall(mensagem.encode('utf-8'))
           
                else:
                    print(f'Estação {nome_estacao} não está ativa.')      
            
            if partes[0] == "Eleição": # Comunicar a estação o resultado da eleição
                nome_estacao = partes[1]
                vagas = int(partes[2])
                
                # Vagas que a estação lider já tem
                vagas_estacao = self.estacao_vagas.get(nome_estacao, 0)
                # Soma com as vagas vindo da eleição
                vagas = vagas_estacao + vagas
                
                vagas_ocupadas_estacao = self.vagas_ocupadas.get(nome_estacao, 0)
                vagas_ocupadas = int(partes[3])
                vagas_ocupadas = vagas_ocupadas_estacao + vagas_ocupadas
                
                # Colocar a lista de carros estacionados
                if partes[4] == "None":
                    carros = []
                else:   
                    carros = partes[4]
                    id_carros = carros.split('.')
                    for id_carro in id_carros:
                        self.id_carros[nome_estacao].append(id_carro)
        
                self.vagas_ocupadas[nome_estacao] = vagas_ocupadas
                self.estacao_vagas[nome_estacao] = vagas
                
                self.enviar_mensagem_estacao(nome_estacao, f'Gerente Alocação {vagas} {vagas_ocupadas} {carros}')
            
            elif partes[0] == "Estacionado":
                
                self.vagas_ocupadas[partes[1]] += 1
                self.id_carros[partes[1]].append(partes[2])
                
                resposta = f'Registro de estacionamento no gerente'
                cliente_socket.sendall(resposta.encode('utf-8'))
            
            elif partes[0] == "Saida":
                self.vagas_ocupadas[partes[1]] -= 1
          
                self.id_carros[partes[1]].remove(partes[2])
             
                resposta = f'Registro de saída no gerente'
                cliente_socket.sendall(resposta.encode('utf-8'))
                
                
        cliente_socket.close()

    def atualizar_referencias_circular(self):
        """ Atualiza as referências para manter uma fila circular """
        estacoes_lista = list(self.estacoes_ativas.keys())

        if len(estacoes_lista) > 1:
            self.conexoes.clear()  # Limpa as conexões atuais
            
            for i in range(len(estacoes_lista)):
                estacao_atual = estacoes_lista[i]
                proxima_estacao = estacoes_lista[(i + 1) % len(estacoes_lista)]
                
                ip, porta = self.estacoes_ativas[proxima_estacao]
                self.conexoes[estacao_atual] = (proxima_estacao, ip, porta)
                
                mensagem = f'Conexão {proxima_estacao} {ip} {porta}'
                self.enviar_mensagem_estacao(estacao_atual, mensagem)
            

    def encontrar_estacao_x(self, nome_estacao):
        """ Encontra a estação que esta conectada a estação que será desativada """
        
        for estacao_conectada, estacao_referencia_info in self.conexoes.items():
            estacao_referencia_nome = estacao_referencia_info[0]  # Nome da estação referenciada
            if estacao_referencia_nome == nome_estacao:
                return estacao_conectada  # Retorna a estação conectada que referencia `nome_estacao`

        return None  # Caso nenhuma estação esteja referenciando `nome_estacao`

    def distribuir_vagas(self):
        """ Distribui as vagas de forma aleatória entre todas as estações ativas """
        if len(self.estacoes_ativas) > 0:
            vagas_por_estacao = [0] * len(self.estacoes_ativas)

            for _ in range(self.vagas_estacionamento):
                estacao_escolhida = random.randint(0, len(self.estacoes_ativas) - 1)
                vagas_por_estacao[estacao_escolhida] += 1

            for i, (nome_estacao, _) in enumerate(self.estacoes_ativas.items()):
                self.estacao_vagas[nome_estacao] = vagas_por_estacao[i]
                print(f'Estação {nome_estacao} recebeu {vagas_por_estacao[i]} vagas.')


    def informar_vagas_estacoes(self):
        """ Envia a quantidade de vagas para cada estação ativa via TCP """
        for nome_estacao, (ip, porta) in self.estacoes_ativas.items():
            
            vagas = self.estacao_vagas.get(nome_estacao, 0)
            mensagem = f"Alocação {vagas}"
            
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((ip, porta))
                    s.sendall(mensagem.encode('utf-8'))
                    print(f'Enviado para {nome_estacao} ({ip}:{porta}): {mensagem}')
            except Exception as e:
                print(f'Erro ao conectar com a estação {nome_estacao}: {e}')
        
    
    def enviar_mensagem_estacao(self, nome_estacao, mensagem):
        
        ip, porta = self.estacoes_ativas[nome_estacao]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, porta))
                s.sendall(mensagem.encode('utf-8'))
                print(f'Enviado para {nome_estacao} ({ip}:{porta}): {mensagem}')
                
                s.close()
        except Exception as e:
            print(f'Erro ao conectar com a estação {nome_estacao}: {e}')
            
            
    def registrar_estacao(self, nome, ip, porta):
        """ Registra a estação como ativa no Gerente """
        
        self.estacoes_ativas[nome] = (ip, porta)
        self.vagas_ocupadas[nome] = 0
        self.id_carros[nome] = []
        
        print(f'Estação {nome} registrada {porta} como ativa no Gerente.')
        

    def selecionar_proxima_estacao(self):
        """ Seleciona a próxima estação ativa de forma balanceada (round-robin) """
        estacoes_lista = list(self.estacoes_ativas.items())

        # Seleciona a próxima estação com base no índice
        estacao_selecionada = estacoes_lista[self.estacao_index % len(estacoes_lista)]
        self.estacao_index += 1  # Incrementa o índice para a próxima seleção

        return estacao_selecionada

def main():
    gerente_ip = "127.0.0.1"
    gerente_porta = 8080
    gerente = Gerente(gerente_ip, gerente_porta)
    gerente.iniciar()

if __name__ == "__main__":
    main()
