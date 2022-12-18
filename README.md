# FSE-Trabalho1 - Automação Predial

O sistema de automação predial construído conta com dois arquivos principais, o ```server.py``` que contém o servidor central, e o ```client.py``` que contém o servidor distribuído. O servidor central e o distríbuido se comunicam através de sockets tcp/ip. Para detalhes dos requisitos acesse o link [especificação](https://gitlab.com/fse_fga/trabalhos-2022_2/trabalho-1-2022-2).

Para visualizar a execução da solução acesse o vídeo ```apresentacao.mkv``` listado nesse repositório.

## Instalação

**Pré requisitos:**
  - python
  - git
  - venv (opcional)

Para instalar execute os comandos:

1 - Baixe o repositório
```bash
git clone https://github.com/CarlosFiuza/FSE-Trabalho1.git
```

2 - Entre na pasta
```bash
cd FSE-Trabalho1
```

3 - Crie um ambiente virtual (Opcional)
```bash
python3 -m venv virtualenv/
```

4 - Instale as dependências
```bash
python3 -m pip install -r requirements.txt
```

5 - Carregue o ambiente virtual (Opcional e se passo 3 executado)
```bash
source virtualenv/bin/activate
```

6 - Execute o servidor central passando endereço e porta que desejar (lembre-se de atualizar o endereço e porta nos arquivos de configuração config_room1.json e config_room2.json)
```bash
python3 server.py endereco porta
```

7 - Execute o servidor distribuído passando como argumento o caminho do arquivo de configuração (config_room1.json para sala 01 e 03 e config_room2.json para sala 02 e 04)
```bash
python3 client.py config_room1.json
```

## Uso

A visualização dos estados dos sensores de entrada e saída de cada sala são visualizadas através do console do servidor central, assim como estado do sistema de alarme e total de pessoas no prédio, além de ser a entrada para comandos aos servidores distribuídos.

Sendo assim:

- Instruções, feedbacks e erros que acontecem no servidor central possuem cor amarela.
- Feedbacks de comandos requisitados para o servidor distribuído possuem cor verde (tanto feedbacks de sucesso quanto de mal-sucedidos).
- Erros graves que podem acontecer durante a execução possuem cor vermelha.
- Informações sobre o prédio e a sala possuem cor ciano.
- Nas instruções de comandos temos alguns termos recorrentes:
  - \<room\> : é requisitado o nome da sala, por exemplo "Sala 01"
  - \<output\> : é requisitado o nome do sensor de saída, conforme aparece na listagem. Exemplo "Lâmpada 01"
  - \<value\> : é requisitado um valor para setar o sensor de saída, sendo que 0 irá desligar e 1 irá ligá-lo.
