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
- Roles permitidos
- Usuários permitidos
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

**Requer:**
- Estar na lista de `usuarios_permitidos` OU
- Ter uma das `roles_permitidos`

---

## Configurações (`config.json`)

### Preferências Alimentares
```json
"preferencias_sem": {
    "123456789": "MACARRÃO",
    "987654321": "FEIJÃO"
}
```

### Termos Restritos
```json
"termos_restritos": {
    "MACARRÃO": ["macarrão", "macarrao", "espaguete", "talharim", "nhoque"]
}
```

### Permissões
```json
"roles_permitidos": ["Admin", "Gestor", "RH"],
"usuarios_permitidos": ["123456789"]
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
- **ID do canal** configurado no `.env`
- **Número WhatsApp** configurado no `.env`
