import pytest
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

def validar_numero_whatsapp(numero):
    if not numero:
        return None
    numero_limpo = re.sub(r'\D', '', numero)
    if len(numero_limpo) >= 10:
        return numero_limpo
    return None


def limpar_cardapio(texto: str, filtros: list) -> list:
    texto = texto.replace('*', '')
    linhas = texto.split('\n')
    pratos_unicos = []

    for linha in linhas:
        item = linha.strip()
        item_lower = item.lower()
        if not item or len(item) < 5:
            continue
        if any(termo in item_lower for termo in filtros):
            continue
        
        item_limpo = re.sub(r'^[^\w\s]*[\d\.\-\*]*\s*', '', item)
        if item_limpo and item_limpo.lower() not in [p.lower() for p in pratos_unicos]:
            pratos_unicos.append(item_limpo)
    return pratos_unicos


def montar_linha_prato(prato: str, qtd: int, votos_por_usuario: dict, preferencias: dict) -> str:
    usuarios_com_restricao = []
    
    for user_id, restricao in preferencias.items():
        if prato in votos_por_usuario.get(user_id, []):
            usuarios_com_restricao.append(restricao)

    qtd_sem = len(usuarios_com_restricao)

    if qtd_sem == 0:
        return f"{qtd:02d} {prato}"

    obs_texto = " / ".join(set(usuarios_com_restricao))

    if qtd_sem == qtd:
        return f"{qtd:02d} {prato} (SEM {obs_texto})"
    else:
        return f"{qtd:02d} {prato} ({qtd_sem:02d} SEM {obs_texto})"


class TestValidarNumeroWhatsApp:
    def test_numero_valido_com_ddd(self):
        assert validar_numero_whatsapp("5511999999999") == "5511999999999"
    
    def test_numero_valido_apenas_digitos(self):
        assert validar_numero_whatsapp("11999999999") == "11999999999"
    
    def test_numero_valido_com_mascara(self):
        assert validar_numero_whatsapp("(11) 99999-9999") == "11999999999"
    
    def test_numero_none(self):
        assert validar_numero_whatsapp(None) is None
    
    def test_numero_vazio(self):
        assert validar_numero_whatsapp("") is None
    
    def test_numero_curto(self):
        assert validar_numero_whatsapp("123456") is None


class TestLimparCardapio:
    FILTROS = ["arroz branco", "feijão com caldo", "batata frita", "obrigada"]
    
    def test_prato_valido(self):
        texto = "Frango Grelhado com legumes"
        result = limpar_cardapio(texto, self.FILTROS)
        assert "Frango Grelhado com legumes" in result
    
    def test_remove_acompanhamentos(self):
        texto = "Frango\nArroz Branco\nFeijão com Caldo\nBatata Frita"
        result = limpar_cardapio(texto, self.FILTROS)
        assert len(result) == 1
        assert "Arroz Branco" not in result
        assert "Batata Frita" not in result
    
    def test_remove_linhas_curtas(self):
        texto = "abc\nFrango Assado"
        result = limpar_cardapio(texto, self.FILTROS)
        assert "abc" not in result
        assert "Frango Assado" in result
    
    def test_remove_duplicatas_case_insensitive(self):
        texto = "Frango Grelhado\nfrango grelhado\nFRANGO GRELHADO"
        result = limpar_cardapio(texto, self.FILTROS)
        assert len(result) == 1
    
    def test_remove_numeros_iniciais(self):
        texto = "1- Frango Grelhado\n2. Arroz"
        result = limpar_cardapio(texto, self.FILTROS)
        assert "Frango Grelhado" in result
    
    def test_cardapio_vazio(self):
        result = limpar_cardapio("Arroz Branco\nFeijão com Caldo", self.FILTROS)
        assert len(result) == 0


class TestMontarLinhaPrato:
    PREFERENCIAS = {123: "MACARRÃO", 456: "FEIJÃO"}
    
    def test_sem_restricao(self):
        votos = {}
        result = montar_linha_prato("FRANGO GRELHADO", 5, votos, self.PREFERENCIAS)
        assert result == "05 FRANGO GRELHADO"
    
    def test_com_restricao_parcial(self):
        votos = {123: ["FRANGO GRELHADO"]}
        result = montar_linha_prato("FRANGO GRELHADO", 5, votos, self.PREFERENCIAS)
        assert result == "05 FRANGO GRELHADO (01 SEM MACARRÃO)"
    
    def test_com_restricao_total(self):
        votos = {123: ["FRANGO GRELHADO"]}
        result = montar_linha_prato("FRANGO GRELHADO", 1, votos, self.PREFERENCIAS)
        assert result == "01 FRANGO GRELHADO (SEM MACARRÃO)"
    
    def test_multiplas_restricoes_mesmo_usuario(self):
        preferencias = {123: "MACARRÃO"}
        votos = {}
        result = montar_linha_prato("FRANGO GRELHADO", 3, votos, preferencias)
        assert result == "03 FRANGO GRELHADO"


class TestValidacoesIntegracao:
    def test_wpp_valido_gera_url_correta(self):
        import urllib.parse
        numero = validar_numero_whatsapp("5511999999999")
        texto = "Teste"
        url = f"https://wa.me/{numero}?text={urllib.parse.quote(texto)}"
        assert "wa.me/5511999999999" in url
    
    def test_filtro_case_insensitive(self):
        filtros = ["macarrão"]
        texto = "Frango com Macarrão\nMacarrão"
        result = limpar_cardapio(texto, filtros)
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
