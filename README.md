# 🔐 Controle de Acesso RFID — Sala do Projeto

Sistema de controle de acesso desenvolvido com Raspberry Pi 4B e leitor RFID MFRC522. Realiza leitura de tags de colaboradores, verifica autorização de acesso, monitora tempo de permanência na sala e registra tentativas não autorizadas. Possui interface web em tempo real para acompanhamento via navegador.

---

## 👥 Grupo

| Nome | RA |
|---|---|
| Matheus Durigon Rodrigues | 1134695 |
| Erick De Nardi | 1134724 |
| João Inácio | 1135445 |
| Luis Zanin | 1136493 |

---

## ⚙️ Funcionalidades

- Leitura de tag RFID e verificação de acesso
- Mensagem de **"Bem-vindo"** na primeira entrada do dia ou **"Bem-vindo de volta"** em entradas subsequentes
- Registro de **entrada e saída** via leitura da mesma tag (toggle)
- Monitoramento do **tempo de permanência** por colaborador
- Identificação de **tentativas de acesso não autorizado** (colaborador cadastrado sem permissão)
- Identificação de **tentativas de invasão** (tag desconhecida) com 10 piscadas do LED vermelho
- **Interface web** com atualização em tempo real (polling a cada 2s)
- **Download do relatório** em CSV diretamente pelo navegador
- Relatório completo exibido no terminal ao encerrar com `Ctrl+C`
- **Debounce** de 3 segundos para evitar leituras duplicadas

---

## 🔌 Hardware

- Raspberry Pi 4B
- Leitor RFID MFRC522
- 1x LED Verde
- 1x LED Vermelho
- 2x Resistor 330Ω
- Protoboard + jumpers

### Pinout — MFRC522

| MFRC522 | Pino Físico | GPIO (BCM) |
|---|---|---|
| SDA | 24 | GPIO8 |
| SCK | 23 | GPIO11 |
| MOSI | 19 | GPIO10 |
| MISO | 21 | GPIO9 |
| RST | 22 | GPIO25 |
| GND | 20 | GND |
| 3.3V | 17 | 3V3 |

### Pinout — LEDs

| Componente | Pino Físico | GPIO (BCM) |
|---|---|---|
| LED Verde (anodo) | 5 | GPIO3 |
| LED Vermelho (anodo) | 3 | GPIO2 |
| GND (compartilhado) | 6 / 9 | GND |

---

## 📁 Estrutura do Projeto

```
rfid_web/
├── app.py                  # Backend Flask + lógica RFID
└── templates/
    └── index.html          # Interface web
```

---

## 🚀 Como Executar

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/seu-repo.git
cd seu-repo
```

### 2. Criar e ativar o ambiente virtual

```bash
python3 -m venv .venv
```

### 3. Instalar dependências

```bash
.venv/bin/pip install flask mfrc522 RPi.GPIO
```

### 4. Executar

```bash
sudo .venv/bin/python app.py
```

> `sudo` é necessário para acesso ao GPIO.

### 5. Acessar a interface web

Descubra o IP do Raspberry Pi:

```bash
hostname -I
```

Acesse no navegador de qualquer dispositivo na mesma rede:

```
http://<IP-DO-RASPBERRY>:5000
```

---

## 📋 Comportamento do Sistema

| Situação | Terminal | LED |
|---|---|---|
| Tag desconhecida | "Identificação não encontrada!" | 🔴 Pisca 10x |
| Cadastrado sem acesso | "Você não tem acesso a este projeto, {nome}" | 🔴 Aceso 5s |
| Entrada autorizada (1ª no dia) | "Bem-vindo, {nome}" | 🟢 Aceso 5s |
| Entrada autorizada (retorno) | "Bem-vindo de volta, {nome}" | 🟢 Aceso 5s |
| Saída registrada | "Até logo, {nome}" | 🟢 Aceso 2s |

---

## 📊 Relatório Final

Ao pressionar `Ctrl+C`, o sistema exibe no terminal:

- Tempo total de permanência por colaborador
- Tentativas de acesso de colaboradores sem autorização (nome + quantidade)
- Total de tentativas de invasão com tags desconhecidas

O mesmo relatório pode ser baixado em `.csv` pela interface web.
