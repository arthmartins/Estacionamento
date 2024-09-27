import socket
import threading
import random
import re

class Gerente:
    def __init__(self, ip, porta):
        self.ip = ip
        self.porta = porta
        self.vagas_estacionamento = 20
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

                # Verifica se há outras estações ativas para formar a árvore
                if len(self.estacoes_ativas) > 1:
                    # Usa o índice para selecionar a próxima estação para se conectar (round-robin)
                    estacao_referencia = self.selecionar_proxima_estacao()
                    ip_ref, porta_ref = estacao_referencia[1]
                    self.conexoes[nome_estacao] = estacao_referencia[0]
                    cliente_socket.sendall(f'Conexão: {estacao_referencia[0]} {ip_ref} {porta_ref}'.encode('utf-8'))
                    
                else:
                    # Primeira estação, não precisa de árvore
                    cliente_socket.sendall('Primeira estação ativa'.encode('utf-8'))
            
            if partes[0] == "Desativar":
                nome_estacao = partes[1]
                if nome_estacao in self.estacoes_ativas:
                    
                    vagas = self.estacao_vagas.get(nome_estacao, 0)
                    
                    estacao_referencia = self.conexoes.get(nome_estacao)
                    estacao_conectada = self.encontrar_estacao_x(nome_estacao)
                    
                    if estacao_conectada in self.conexoes:
                        del self.conexoes[estacao_conectada]
                    
                    if estacao_referencia is not None:
                        
                        if estacao_conectada is not None:
                            estacao_completa = self.estacoes_ativas.get(estacao_conectada)
                            estacao_completa_formatada = (estacao_conectada,) + estacao_completa
                            self.enviar_mensagem_estacao(estacao_referencia, f"Trocar conexão {estacao_completa_formatada}")
                        else:
                            self.enviar_mensagem_estacao(estacao_referencia, f"Trocar conexão {None}")
                            
                        if estacao_conectada is not None:
                            estacao_completa = self.estacoes_ativas.get(estacao_referencia)
                            estacao_completa_formatada = (estacao_referencia,) + estacao_completa

                            self.enviar_mensagem_estacao(estacao_conectada, f"Trocar referência {estacao_completa_formatada}")
                            self.conexoes[estacao_conectada] = estacao_referencia
                        
                    else:
                        self.enviar_mensagem_estacao(estacao_conectada, f"Trocar referência {None}")
                    
                    if nome_estacao in self.conexoes:
                        del self.conexoes[nome_estacao]
                                        
                    del self.estacoes_ativas[nome_estacao]
                    print(f'GERENTE {nome_estacao} desativada.')
                    
                    # vagas_ocupadas = self.vagas_ocupadas.get(nome_estacao, 0)
                    # carros = []
                    # if nome_estacao in self.id_carros:
                    #     carros = self.id_carros.get(nome_estacao, [])
                    #     del self.id_carros[nome_estacao]
                    
                    # del self.vagas_ocupadas[nome_estacao]
                    
                    # mensagem = f'{vagas} {vagas_ocupadas} {carros}'
                    mensagem = f'{vagas}'
                    cliente_socket.sendall(mensagem.encode('utf-8'))

                else:
                    print(f'Estação {nome_estacao} não está ativa.')      
            
            if partes[0] == "Eleição": # Comunicar a estação o resultado da eleição
                nome_estacao = partes[1]
                vagas = int(partes[2])
                
                vagas_estacao = self.estacao_vagas.get(nome_estacao, 0)
                vagas = vagas_estacao + vagas
                
                # vagas_ocupadas_estacao = self.vagas_ocupadas.get(nome_estacao, 0)
                # vagas_ocupadas = int(partes[3])
                # vagas_ocupadas = vagas_ocupadas_estacao + vagas_ocupadas
                
                # carros = partes[4:]
                
                # carros_str = str(carros).replace('[', '').replace(']', '').replace('"', '').replace("'", "")

                # # Usa regex para capturar palavras alfanuméricas (IDs dos carros)
                # matches = re.findall(r'\w+', carros_str)

                # # Faz o append de cada elemento extraído à lista da estação
                # for match in matches:
                #     self.id_carros[nome_estacao].append(match)
                #     print(f'Carro {match} adicionado à estação {nome_estacao}')

                # print(self.id_carros[nome_estacao])  # Saída esperada: ['T8JHFH']
                
                # ids_str = ''.join(carros)
                # ids_limpos = ids_str.strip("[]").replace("'", "").replace(",", "")
                # ids_lista = ids_limpos.split()
            
                # self.vagas_ocupadas[nome_estacao] = vagas_ocupadas
                # self.estacao_vagas[nome_estacao] = vagas
                
                self.enviar_mensagem_estacao(nome_estacao, f'Alocação {vagas}')
            
            elif partes[0] == "Estacionado":
                self.vagas_ocupadas[partes[1]] += 1
            
                self.id_carros[partes[1]].append(partes[2])
                resposta = f'Registro de estacionamento no gerente'
                cliente_socket.sendall(resposta.encode('utf-8'))
            
            elif partes[0] == "Saida":
                self.vagas_ocupadas[partes[1]] -= 1
                print(partes[2])
                print(self.id_carros[partes[1]])
                self.id_carros[partes[1]].remove(partes[2])
                print("Tirou o carro\n\n")
                resposta = f'Registro de saída no gerente'
                cliente_socket.sendall(resposta.encode('utf-8'))
                
                
        cliente_socket.close()


    def encontrar_estacao_x(self, nome_estacao):
        for x, referencia in self.conexoes.items():
            if referencia == nome_estacao:
                return x  # Retorna a chave x que satisfaz a condição

        return None  # Caso nenhuma chave x seja encontrada

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
