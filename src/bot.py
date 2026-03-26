from main import bot, TOKEN, NUMERO_WPP, validar_numero_whatsapp, log, BASE_DIR
import sys
sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    if not TOKEN:
        log.error("❌ DISCORD_TOKEN não encontrado no arquivo .env")
        exit(1)
    
    numero_validado = validar_numero_whatsapp(NUMERO_WPP)
    if not numero_validado:
        log.warning("⚠️ NUMERO_MARMITA não configurado ou inválido no .env")
    
    bot.run(TOKEN, reconnect=True)
