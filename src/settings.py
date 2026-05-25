import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

VALOR_MARMITA_PADRAO = 19
FROZEN = getattr(sys, 'frozen', False)

if FROZEN:
    BASE_DIR = Path(sys._MEIPASS)
    USER_DATA_DIR = Path.home() / "bot_marmita"
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
else:
    BASE_DIR = Path(__file__).parent.parent
    USER_DATA_DIR = BASE_DIR

ENV_PATH = BASE_DIR / ".env"
BUNDLED_CONFIG_PATH = BASE_DIR / "config" / "config.json"
CONFIG_PATH = USER_DATA_DIR / "config.json" if FROZEN else BUNDLED_CONFIG_PATH
HISTORICO_PATH = Path.home() / "bot_marmita" / "historico_pedidos.txt"

if FROZEN:
    LOG_DIR = Path.home() / "bot_marmita"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH = LOG_DIR / "bot.log"
else:
    LOG_DIR = BASE_DIR
    LOG_PATH = BASE_DIR / "bot.log"

load_dotenv(ENV_PATH)

TOKEN = os.getenv('DISCORD_TOKEN')
NUMERO_WPP = os.getenv('NUMERO_MARMITA')
NUMERO_CHEF = os.getenv('NUMERO_CHEF')
CHAVE_PIX = os.getenv('CHAVE_PIX')
NOME_PIX = os.getenv('NOME_PIX', 'IARA SANTANA')


def carregar_valor_marmita(valor_env: Optional[str] = None, logger=None) -> int:
    valor_bruto = os.getenv('VALOR_MARMITA', str(VALOR_MARMITA_PADRAO)) if valor_env is None else valor_env
    try:
        valor = int(str(valor_bruto).strip())
        if valor <= 0:
            raise ValueError
        return valor
    except (TypeError, ValueError):
        if logger:
            logger.warning(f"VALOR_MARMITA inválido ({valor_bruto!r}); usando R$ {VALOR_MARMITA_PADRAO}")
        return VALOR_MARMITA_PADRAO


def carregar_config(config_path: Path = CONFIG_PATH, logger=None) -> dict:
    if FROZEN and config_path == CONFIG_PATH and not config_path.exists() and BUNDLED_CONFIG_PATH.exists():
        try:
            config_path.write_text(BUNDLED_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError as e:
            if logger:
                logger.warning(f"Nao foi possivel criar config local: {e}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        if logger:
            logger.warning(f"config.json não encontrado ou inválido: {e}")
        return {}


def normalizar_usuarios_cadastrados(config: dict, logger=None) -> dict[str, dict]:
    config = config or {}
    usuarios_monitoramento = set()
    for user_id in config.get("usuarios_monitoramento", []):
        try:
            usuarios_monitoramento.add(int(user_id))
        except (TypeError, ValueError):
            if logger:
                logger.warning(f"ID invalido em usuarios_monitoramento ignorado: {user_id!r}")

    usuarios_cadastrados = {}
    cadastro_config = config.get("usuarios_cadastrados", {})
    if isinstance(cadastro_config, dict):
        for user_id, dados in cadastro_config.items():
            try:
                user_id_int = int(user_id)
            except (TypeError, ValueError):
                if logger:
                    logger.warning(f"ID invalido em usuarios_cadastrados ignorado: {user_id!r}")
                continue

            if isinstance(dados, dict):
                nome = str(dados.get("nome") or "").strip()
                monitorar = bool(dados.get("monitorar", user_id_int in usuarios_monitoramento))
            else:
                nome = ""
                monitorar = user_id_int in usuarios_monitoramento

            usuarios_cadastrados[str(user_id_int)] = {
                "nome": nome or f"Usuario {user_id_int}",
                "monitorar": monitorar,
            }

    for user_id_int in usuarios_monitoramento:
        usuarios_cadastrados.setdefault(
            str(user_id_int),
            {"nome": f"Usuario {user_id_int}", "monitorar": True},
        )

    return usuarios_cadastrados


def normalizar_config(config: dict, logger=None) -> dict:
    config = config or {}
    preferencias_sem = {}
    for user_id, restricao in config.get("preferencias_sem", {}).items():
        try:
            preferencias_sem[int(user_id)] = restricao
        except (TypeError, ValueError):
            if logger:
                logger.warning(f"ID inválido em preferencias_sem ignorado: {user_id!r}")

    usuarios_monitoramento = set()
    for user_id in config.get("usuarios_monitoramento", []):
        try:
            usuarios_monitoramento.add(int(user_id))
        except (TypeError, ValueError):
            if logger:
                logger.warning(f"ID inválido em usuarios_monitoramento ignorado: {user_id!r}")

    usuarios_cadastrados = normalizar_usuarios_cadastrados(config, logger=logger)

    return {
        "preferencias_sem": preferencias_sem,
        "usuarios_monitoramento": usuarios_monitoramento,
        "usuarios_cadastrados": usuarios_cadastrados,
        "limite_mensagens": config.get("limite_mensagens", 100),
        "enquete_duracao_horas": config.get("enquete_duracao_horas", 4),
        "total_maximo_marmitas": config.get("total_maximo_marmitas", 200),
    }
