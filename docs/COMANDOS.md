# 🍴 Bot Marmita - Comandos

## Comandos de Pedido

### `!almoco` / `!almoço` / `!cardapio` / `!cardápio`
Envia o cardápio como enquete no canal configurado.

**Uso:**
```
!almoco [cole aqui o cardápio copiado]
```

**Exemplo:**
```
!almoco
Omelete de queijo
Filé de frango acebolado
Filé de frango à milanesa
Parmegiana de frango
Arroz branco
Feijão com caldo
...
```

---

### `!pedido` / `!fechar` / `!finalizar`
Fecha a votação e gera o pedido consolidado para WhatsApp.

**Uso:**
```
!pedido
```

**Saída:**
- Total de marmitas
- Lista de pratos com quantidades
- Observações de restrições (ex: "SEM MACARRÃO")
- Link do WhatsApp para envio
- Link de cobrança PIX, quando `NUMERO_CHEF` e `CHAVE_PIX` estiverem configurados

---

## Comandos de Informação

### `!pref` / `!preferencias`
Lista as restrições alimentares configuradas.

**Uso:**
```
!pref
```

---

### `!status`
Mostra o status completo do bot.

**Uso:**
```
!status
```

**Exibe:**
- Usuário do bot
- Quantidade de servidores
- Quantidade de canais
- Número de restrições ativas
- Limite de mensagens
- Status do WhatsApp

---

## Comandos Administrativos

### `!reload` / `!recarregar`
Recarrega as configurações do arquivo `config.json` sem reiniciar o bot.

**Uso:**
```
!reload
```

---

## Configurações (`config.json`)

### Preferências Alimentares
```json
"preferencias_sem": {
    "123456789": "MACARRÃO",
    "987654321": "FEIJÃO"
}
```

### Limites
```json
"limite_mensagens": 100,
"enquete_duracao_horas": 4,
"total_maximo_marmitas": 200
```

---

## Requisitos

- **Discord Token** configurado no `.env`
- **Número WhatsApp** configurado no `.env`
- **PIX e número do responsável** configurados no `.env`, caso queira gerar o link de cobrança

### Variáveis de ambiente
```env
DISCORD_TOKEN=seu_token_do_bot
NUMERO_MARMITA=5511999999999
NUMERO_CHEF=5511988887777
CHAVE_PIX=sua_chave_pix
NOME_PIX=IARA SANTANA
VALOR_MARMITA=18
```

Se `VALOR_MARMITA` estiver ausente ou inválido, o bot usa `18`. O link de cobrança só é gerado quando `NUMERO_CHEF` é válido e `CHAVE_PIX` está preenchida.
