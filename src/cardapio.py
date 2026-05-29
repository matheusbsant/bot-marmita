import re
import unicodedata


def _nfc(text: str) -> str:
    return unicodedata.normalize('NFC', text)


def limpar_cardapio(texto: str) -> list[dict]:
    pratos_unicos = []
    texto_nfc = _nfc(texto)
    texto_negrito = re.findall(r'\*([^*]+)\*', texto_nfc)
    linhas = texto_nfc.split('\n')

    for negrito in texto_negrito:
        prato_nome = negrito.strip()

        if len(prato_nome) <= 5 or len(prato_nome) > 150:
            continue
        if any(_nfc(p['nome']) == _nfc(prato_nome) for p in pratos_unicos):
            continue

        tem_macarrao = False
        linha_prato_idx = -1
        linha_alvo = _nfc(f"*{prato_nome}*")

        for idx, linha in enumerate(linhas):
            if _nfc(linha.strip()) == linha_alvo:
                linha_prato_idx = idx
                break

        if linha_prato_idx == -1:
            continue

        tem_conteudo_abaixo = False
        tem_palavra_macarrao_abaixo = False

        for j in range(linha_prato_idx + 1, len(linhas)):
            linha_strip = linhas[j].strip()

            if not linha_strip:
                continue
            if linha_strip.lstrip().startswith('*'):
                break

            linha_lower = linha_strip.lower()
            if not linha_lower.startswith('http'):
                tem_conteudo_abaixo = True
            if 'macarrão' in linha_lower or 'macarrao' in linha_lower:
                tem_palavra_macarrao_abaixo = True

        if not tem_conteudo_abaixo:
            tem_macarrao = True
        elif tem_palavra_macarrao_abaixo:
            tem_macarrao = True

        pratos_unicos.append({
            'nome': _nfc(prato_nome),
            'tem_macarrao': tem_macarrao,
        })

    return pratos_unicos
