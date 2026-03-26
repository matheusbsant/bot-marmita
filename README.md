# 🍴 Bot Marmita

Sistema automático de pedidos de almoço via Discord com interface gráfica (tkinter).

## 📁 Estrutura do Projeto

```
bot-marmita/
├── src/
│   ├── main.py            # Lógica do bot
│   ├── bot.py             # Ponto de entrada do bot
│   ├── interface.py       # Interface gráfica (tkinter)
│   └── test_main.py       # Testes unitários
├── config/
│   ├── config.json        # Configurações locais (NÃO COMITAR)
│   └── config.example.json # Template de configuração
├── docs/
│   ├── README.md
│   └── COMANDOS.md
├── dist/
│   └── BotMarmita/        # Executável gerado
│       └── BotMarmita.exe
├── .env                   # Variáveis de ambiente (NÃO COMITAR)
├── interface.spec         # Configuração PyInstaller
└── requirements.txt
```

## 🚀 Como Usar

### Opção 1: Executável (Recomendado)

1. Baixe a pasta `dist/BotMarmita/`
2. Copie para o local desejado
3. Edite `.env` e `config/config.json` dentro da pasta `_internal/`
4. Execute `BotMarmita.exe`
5. Crie um atalho na área de trabalho se desejar

**Logs são salvos em:** `C:\Users\SEU_USUARIO\bot_marmita\`

### Opção 2: Código Fonte

```bash
# Clone o repositório
git clone https://github.com/matheusbsant/bot-marmita.git
cd bot-marmita

# Instale dependências
pip install -r requirements.txt

# Configure o .env
cp config/config.example.json config/config.json
# Edite config/config.json e .env com seus dados

# Execute
python src/interface.py
# ou
python src/bot.py
```

## ⚙️ Configuração

### 1. Arquivo `.env`

```env
DISCORD_TOKEN=seu_token_do_bot_aqui
NUMERO_MARMITA=5511999999999
```

### 2. Arquivo `config/config.json`

```json
{
    "preferencias_sem": {
        "123456789": "MACARRÃO",
        "987654321": "FRANGO"
    },
    "usuarios_monitoramento": [123456789, 987654321, 111222333],
    "limite_mensagens": 100,
    "enquete_duracao_horas": 4,
    "total_maximo_marmitas": 200
}
```

| Parâmetro | Descrição |
|-----------|-----------|
| `preferencias_sem` | Restrições alimentares (ID Discord → alimento) |
| `usuarios_monitoramento` | IDs para receber lembretes de votação |
| `limite_mensagens` | Mensagens para buscar votações |
| `enquete_duracao_horas` | Duração da enquete |
| `total_maximo_marmitas` | Máximo de marmitas por pedido |

## 📝 Comandos do Bot

| Comando | Descrição |
|---------|-----------|
| `!almoco` | Cria enquete com os pratos do cardápio |
| `!pedido` | Fecha votação e gera pedido para WhatsApp |
| `!pref` | Lista restrições alimentares |
| `!status` | Status do bot |
| `!ajuda` | Mostra comandos disponíveis |

## ⏰ Monitoramento

- Lembrete enviado após **1 hora** se nem todos votaram
- Mensagem de confirmação após todos votarem
- Monitoramento para quando `!pedido` é executado

## 🔧 Dependências

```
discord.py>=2.0.0
python-dotenv>=1.0.0
```

## 📋 Requisitos

- Python 3.10+
- Bot do Discord com intents: `message_content`, `members`, `reactions`
- Permissão "Enviar Mensagens" no canal

## 🔨 Gerar Executável

```bash
pip install pyinstaller
python -m PyInstaller interface.spec --clean -y
```

O executável estará em `dist/BotMarmita/`.

## 📄 Licença

MIT
