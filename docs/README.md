# 🍴 Bot Marmita - Netsul

Sistema automático de pedidos de almoço via Discord.

## 📋 Funcionalidades

- **Criação de enquetes** - Extrai pratos do cardápio automaticamente (texto entre `*asteriscos*`)
- **Monitoramento de votos** - Verifica se todos votaram e envia lembretes
- **Consolidação de pedidos** - Gera pedido formatado para WhatsApp
- **Restrições alimentares** - Marca pratos conforme preferências dos usuários

## 🚀 Como usar

### 1. Clone o repositório

```bash
git clone https://github.com/matheusbsant/bot-marmita.git
cd bot-marmita
```

### 2. Configure o `.env`

```env
DISCORD_TOKEN=seu_token_do_bot
NUMERO_MARMITA=5511999999999
NUMERO_CHEF=5511988887777
CHAVE_PIX=sua_chave_pix
NOME_PIX=IARA SANTANA
VALOR_MARMITA=18
```

As variáveis `NUMERO_CHEF`, `CHAVE_PIX`, `NOME_PIX` e `VALOR_MARMITA` controlam o link opcional de cobrança PIX. A cobrança só é gerada quando `NUMERO_CHEF` é válido e `CHAVE_PIX` está preenchida. Se `VALOR_MARMITA` for inválido, o valor padrão usado é `18`.

### 3. Configure o `config.json`

```json
{
    "preferencias_sem": {
        "ID_USUARIO": "MACARRÃO"
    },
    "usuarios_monitoramento": [123456789, 987654321],
    "limite_mensagens": 100,
    "enquete_duracao_horas": 4,
    "total_maximo_marmitas": 200
}
```

**Parâmetros:**
| Parâmetro | Descrição |
|-----------|-----------|
| `preferencias_sem` | Usuários com restrições alimentares (ID → restrição) |
| `usuarios_monitoramento` | IDs dos usuários para receber lembretes |
| `limite_mensagens` | Limite de mensagens para buscar votações |
| `enquete_duracao_horas` | Duração da enquete no Discord |
| `total_maximo_marmitas` | Máximo de marmitas por pedido |

### 4. Instale e rode

```bash
pip install -r requirements.txt
python src/bot.py
```

## 📝 Comandos

| Comando | Descrição |
|---------|-----------|
| `!almoco` | Cria enquete com os pratos do cardápio |
| `!pedido` | Fecha votação e gera pedido para WhatsApp; gera cobrança PIX quando configurada |
| `!pref` | Lista restrições alimentares |
| `!status` | Status do bot |
| `!ajuda` | Mostra comandos disponíveis |

## ⏰ Monitoramento

- Lembrete é enviado após **1 hora** se nem todos votaram
- Após todos votarem, mensagem de confirmação é enviada
- O monitoramento para quando `!pedido` é executado

## 📁 Estrutura do Projeto

```
├── src/
│   ├── main.py          # Código principal do bot
│   ├── bot.py           # Entrada sem interface
│   ├── interface.py     # Interface gráfica
│   ├── cardapio.py      # Parser do cardápio
│   ├── pedido.py        # Formatação do pedido
│   ├── settings.py      # Configurações e variáveis de ambiente
│   ├── whatsapp.py      # Links de WhatsApp e cobrança
│   └── test_main.py     # Testes unitários
├── config/
│   ├── config.json      # Configurações locais (dados sensíveis)
│   └── config.example.json
├── .env                 # Variáveis de ambiente locais
├── requirements.txt     # Dependências
└── interface.spec       # Configuração PyInstaller
```

## 🔧 Dependências

```
discord.py>=2.0.0
python-dotenv>=1.0.0
pytest>=7.0.0
```

## 📦 Gerar Executável

```bash
pip install pyinstaller
python -m PyInstaller interface.spec --clean -y
```

O executável será gerado na pasta `dist/`.

> ⚠️ O pacote PyInstaller inclui `.env` e `config/` para uso interno. Antes de distribuir fora da equipe, remova ou substitua credenciais e dados sensíveis.

## ⚙️ Requisitos

- Python 3.10+
- Bot do Discord com intents: `message_content`, `members`, `reactions`
- Permissão "Enviar Mensagens" no canal
