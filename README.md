# 🍴 Bot Marmita - Netsul

Sistema automático de pedidos de almoço via Discord.

## 📋 Funcionalidades

- **Criação de enquetes** - Extrai pratos do cardápio automaticamente
- **Monitoramento de votos** - Verifica se todos votaram e envia lembretes
- **Consolidação de pedidos** - Gera pedido formatado para WhatsApp
- **Restrições alimentares** - Marca pratos conforme preferências dos usuários

## 🚀 Como usar

### 1. Configuração

Crie um arquivo `.env` com:

```env
DISCORD_TOKEN=seu_token_do_bot
NUMERO_MARMITA=5511999999999
```

### 2. Configurar o `config.json`

```json
{
    "preferencias_sem": {
        "ID_USUARIO": "MACARRÃO"
    },
    "limite_mensagens": 100,
    "enquete_duracao_horas": 4,
    "total_maximo_marmitas": 200
}
```

### 3. Rodar o bot

```bash
pip install -r requirements.txt
python main.py
```

## 📝 Comandos

| Comando | Descrição |
|---------|-----------|
| `!almoco` | Cria enquete com os pratos do cardápio |
| `!pedido` | Fecha votação e gera pedido para WhatsApp |
| `!pref` | Lista restrições alimentares |
| `!status` | Status do bot |
| `!ajuda` | Mostra comandos disponíveis |

## 👥 Usuários Monitorados

O bot monitora 8 usuários para lembretes de votação. Para adicionar/remover, edite a lista `USUARIOS_SERVIDOR` no `main.py`.

## ⏰ Monitoramento

- Lembrete é enviado após **1 hora** se nem todos votaram
- Após todos votarem, mensagem de confirmação é enviada
- O monitoramento para quando `!pedido` é executado

## 📁 Estrutura do Projeto

```
├── main.py           # Código principal do bot
├── config.json      # Configurações (preferências, limites)
├── .env             # Variáveis de ambiente (TOKEN, WhatsApp)
├── COMANDOS.md      # Documentação dos comandos
├── test_main.py     # Testes unitários
├── requirements.txt  # Dependências
└── main.spec       # Configuração PyInstaller
```

## 🔧 Dependências

```
discord.py>=2.0.0
python-dotenv>=1.0.0
```

## 📦 Gerar Executável

```bash
pip install pyinstaller
pyinstaller main.spec --clean
```

O executável será gerado na pasta `dist/`.

## ⚙️ Requisitos

- Python 3.10+
- Bot do Discord com intents: `message_content`, `members`, `reactions`
- Permissão "Enviar Mensagens" no canal

## 📝 Licença

Este projeto é para uso interno da Netsul Informática.
