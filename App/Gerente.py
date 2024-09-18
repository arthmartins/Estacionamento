import socket
import threading

class Gerente:
    def __init__(self, ip, porta):
        self.ip = ip
        self.porta = porta
        self.estacoes_ativas = {}
        self.estacao_index = 0  # Índice para garantir balanceamento das conexões

    def iniciar(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.bind((self.ip, self.porta))
        servidor.listen(5)
        print(f'Gerente escutando no IP {self.ip}, porta {self.porta}')

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

                # Verifica se há outras estações ativas para formar a árvore
                if len(self.estacoes_ativas) > 1:
                    # Usa o índice para selecionar a próxima estação para se conectar (round-robin)
                    estacao_referencia = self.selecionar_proxima_estacao()
                    ip_ref, porta_ref = estacao_referencia[1]
                    cliente_socket.sendall(f'Conexão: {estacao_referencia[0]} {ip_ref} {porta_ref}'.encode('utf-8'))
                else:
                    # Primeira estação, não precisa de árvore
                    cliente_socket.sendall('Primeira estação ativa'.encode('utf-8'))

        cliente_socket.close()

    def registrar_estacao(self, nome, ip, porta):
        """ Registra a estação como ativa no Gerente """
        self.estacoes_ativas[nome] = (ip, porta)
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
