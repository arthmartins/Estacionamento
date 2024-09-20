As estações são inicializadas lendo o file.txt quando isso acontece é criado uma thread para o app no ip e na porta e uma thread para o middleware. 

O App recebe os comandos da central de controle e a partir dele as coisas são feitas

Alterações:

O middleware tem uma própria porta para se comunicar com outros middlewares, isso vai facilitar mais do que ter só uma porta por ip e estação - para a porta do middleware só adicionei o 1 antes da porta da estação. Ou seja a estação 5, por exemplo, tem a porta 8885, o middleware dela tem a porta 18885

A arvore de encaminhamento foi melhorada, cada middleware agora tem o middleware que vai se conectar (estacao_referencia - a variavel ta como nome estação xd, mas ela leva o nome da estação, o ip, e a porta do middleware) e também tem o middleware que se conectou a ele (variavel - estacao_conectada) isso facilita na hora de percorrer a arvore para as funções

Funções já feitas:

AE - Quando uma estação recebe o AE ela vai ser ativa (o app + o middleware) e ao ser ativa o middleware manda uma msg para o gerente para que o gerente possa guardar a estção ativa
Depois disso o gerente manda o middleware se conectar a alguma outra estação ativa criando a arvore de encaminhamento

VD - Percorre a arvore de encaminhamento a partir de um middleware e vai retornando a estação, a quantidade de vagas disponíveis e a quantidade de vagas ocupadas . É a função processar_vagas no middleware, a partir desse middleware especifico ele vai passando por todos os outros pegando essas infos


Para rodar:

roda primeiro o App.py

Depois roda o Gerente.py 

E por fim o ./main da pasta Controle


