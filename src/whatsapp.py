import re
import urllib.parse
from typing import Optional


def validar_numero_whatsapp(numero: Optional[str]) -> Optional[str]:
    if not numero:
        return None

    numero_limpo = re.sub(r'\D', '', numero)
    if len(numero_limpo) >= 10:
        return numero_limpo
    return None


def montar_link_whatsapp(numero: Optional[str], texto: str) -> Optional[str]:
    numero_validado = validar_numero_whatsapp(numero)
    if not numero_validado:
        return None

    texto_url = urllib.parse.quote(texto)
    return f"https://wa.me/{numero_validado}?text={texto_url}"


def montar_link_cobranca(
    total_marmitas: int,
    numero_chef: Optional[str],
    chave_pix: Optional[str],
    nome_pix: str,
    valor_marmita: int,
    logger=None,
) -> Optional[str]:
    numero_chef_validado = validar_numero_whatsapp(numero_chef)
    chave_pix_limpa = (chave_pix or "").strip()

    if not numero_chef_validado:
        if logger:
            logger.info("Cobrança PIX não gerada: NUMERO_CHEF ausente ou inválido.")
        return None
    if not chave_pix_limpa:
        if logger:
            logger.info("Cobrança PIX não gerada: CHAVE_PIX ausente.")
        return None

    total_pagar = total_marmitas * valor_marmita
    mensagem_cobranca = (
        f"Total a pagar: {total_marmitas} x R$ {valor_marmita} = R$ {total_pagar}\n"
        f"PIX: {chave_pix_limpa} ({nome_pix})"
    )
    return montar_link_whatsapp(numero_chef_validado, mensagem_cobranca)
