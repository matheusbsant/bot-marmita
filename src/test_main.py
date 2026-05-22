import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import main
from cardapio import limpar_cardapio
from interface import aplicar_usuarios_no_config, usuarios_para_interface
from pedido import montar_corpo_pedido, montar_linha_prato
from settings import VALOR_MARMITA_PADRAO, carregar_valor_marmita, normalizar_config
from whatsapp import montar_link_cobranca, montar_link_whatsapp, validar_numero_whatsapp


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


class TestValorMarmita:
    def test_valor_valido(self):
        assert carregar_valor_marmita("22") == 22

    @pytest.mark.parametrize("valor", ["abc", "", "0", "-5", None])
    def test_valor_invalido_usa_padrao(self, valor):
        assert carregar_valor_marmita(valor) == VALOR_MARMITA_PADRAO


class TestConfig:
    def test_normaliza_config_com_ids_validos(self):
        config = {
            "preferencias_sem": {"123": "MACARRÃO"},
            "usuarios_monitoramento": ["123", 456],
            "limite_mensagens": 50,
            "enquete_duracao_horas": 2,
            "total_maximo_marmitas": 80,
        }

        result = normalizar_config(config)

        assert result["preferencias_sem"] == {123: "MACARRÃO"}
        assert result["usuarios_monitoramento"] == {123, 456}
        assert result["limite_mensagens"] == 50
        assert result["enquete_duracao_horas"] == 2
        assert result["total_maximo_marmitas"] == 80

    def test_normaliza_config_ignora_ids_invalidos(self):
        config = {
            "preferencias_sem": {"abc": "MACARRÃO", "123": "FEIJÃO"},
            "usuarios_monitoramento": ["xyz", 456],
        }

        result = normalizar_config(config)

        assert result["preferencias_sem"] == {123: "FEIJÃO"}
        assert result["usuarios_monitoramento"] == {456}


    def test_normaliza_config_antigo_cria_cadastro_de_usuarios(self):
        config = {"usuarios_monitoramento": ["123", 456]}

        result = normalizar_config(config)

        assert result["usuarios_cadastrados"] == {
            "123": {"nome": "Usuario 123", "monitorar": True},
            "456": {"nome": "Usuario 456", "monitorar": True},
        }

    def test_normaliza_config_novo_mantem_ativos_e_inativos(self):
        config = {
            "usuarios_cadastrados": {
                "123": {"nome": "Ana", "monitorar": True},
                "456": {"nome": "Bruno", "monitorar": False},
                "abc": {"nome": "Invalido", "monitorar": True},
            },
            "usuarios_monitoramento": ["123", "123"],
        }

        result = normalizar_config(config)

        assert result["usuarios_monitoramento"] == {123}
        assert result["usuarios_cadastrados"] == {
            "123": {"nome": "Ana", "monitorar": True},
            "456": {"nome": "Bruno", "monitorar": False},
        }

    def test_interface_aplica_usuarios_preservando_demais_configuracoes(self):
        config = {
            "preferencias_sem": {"999": "MACARRÃƒO"},
            "limite_mensagens": 50,
            "usuarios_monitoramento": [999],
        }
        usuarios = [
            {"id": "111", "nome": "Ana", "monitorar": True},
            {"id": "222", "nome": "Bruno", "monitorar": False},
        ]

        result = aplicar_usuarios_no_config(config, usuarios)

        assert result["preferencias_sem"] == {"999": "MACARRÃƒO"}
        assert result["limite_mensagens"] == 50
        assert result["usuarios_monitoramento"] == [111]
        assert result["usuarios_cadastrados"] == {
            "111": {"nome": "Ana", "monitorar": True},
            "222": {"nome": "Bruno", "monitorar": False},
        }

    def test_interface_reativa_exclui_e_nome_vazio_usa_padrao(self):
        config = {
            "usuarios_cadastrados": {
                "111": {"nome": "Ana", "monitorar": False},
                "222": {"nome": "Bruno", "monitorar": True},
            },
            "usuarios_monitoramento": [222],
        }
        usuarios = [
            {"id": "111", "nome": "", "monitorar": True},
        ]

        result = aplicar_usuarios_no_config(config, usuarios)

        assert result["usuarios_monitoramento"] == [111]
        assert result["usuarios_cadastrados"] == {
            "111": {"nome": "Usuario 111", "monitorar": True},
        }
        assert usuarios_para_interface(result) == [
            {"id": "111", "nome": "Usuario 111", "monitorar": True},
        ]

    def test_interface_rejeita_usuario_duplicado_ou_invalido(self):
        with pytest.raises(ValueError):
            aplicar_usuarios_no_config({}, [{"id": "abc", "nome": "Ana", "monitorar": True}])

        with pytest.raises(ValueError):
            aplicar_usuarios_no_config(
                {},
                [
                    {"id": "111", "nome": "Ana", "monitorar": True},
                    {"id": "111", "nome": "Bruno", "monitorar": False},
                ],
            )


class TestLimparCardapio:
    def test_identifica_prato_com_macarrao(self):
        texto = "*Frango Grelhado*\nArroz branco\nMacarrão ao alho"
        result = limpar_cardapio(texto)
        assert result == [{"nome": "Frango Grelhado", "tem_macarrao": True}]

    def test_identifica_prato_sem_macarrao(self):
        texto = "*Carne Assada*\nArroz branco\nFeijão com caldo\nSalada"
        result = limpar_cardapio(texto)
        assert result == [{"nome": "Carne Assada", "tem_macarrao": False}]

    def test_prato_sem_detalhes_assume_macarrao(self):
        texto = "*Omelete de Queijo*"
        result = limpar_cardapio(texto)
        assert result == [{"nome": "Omelete de Queijo", "tem_macarrao": True}]

    def test_remove_duplicatas_case_insensitive(self):
        texto = "*Frango Grelhado*\nMacarrão\n*frango grelhado*\nMacarrão"
        result = limpar_cardapio(texto)
        assert result == [{"nome": "Frango Grelhado", "tem_macarrao": True}]

    def test_multiplos_pratos(self):
        texto = "*Frango Grelhado*\nMacarrão\n*Carne Assada*\nArroz branco"
        result = limpar_cardapio(texto)
        assert result == [
            {"nome": "Frango Grelhado", "tem_macarrao": True},
            {"nome": "Carne Assada", "tem_macarrao": False},
        ]

    def test_cardapio_sem_negrito_retorna_vazio(self):
        assert limpar_cardapio("Frango\nArroz Branco") == []


class TestMontarLinhaPrato:
    def test_sem_restricao(self):
        assert montar_linha_prato("FRANGO GRELHADO", 5, {}, {}, True) == "05 FRANGO GRELHADO"

    def test_com_restricao_parcial(self):
        preferencias = {123: "MACARRÃO"}
        votos = {123: ["FRANGO GRELHADO"]}
        result = montar_linha_prato("FRANGO GRELHADO", 5, votos, preferencias, True)
        assert result == "05 FRANGO GRELHADO (01 SEM MACARRÃO)"

    def test_com_restricao_total(self):
        preferencias = {123: "MACARRÃO"}
        votos = {123: ["FRANGO GRELHADO"]}
        result = montar_linha_prato("FRANGO GRELHADO", 1, votos, preferencias, True)
        assert result == "01 FRANGO GRELHADO (SEM MACARRÃO)"

    def test_ignora_restricao_quando_prato_nao_tem_macarrao(self):
        preferencias = {123: "MACARRÃO"}
        votos = {123: ["CARNE ASSADA"]}
        result = montar_linha_prato("CARNE ASSADA", 1, votos, preferencias, False)
        assert result == "01 CARNE ASSADA"


class TestCorpoPedido:
    def test_monta_corpo_pedido(self):
        corpo = montar_corpo_pedido("29.04.2026", ["02 FRANGO", "01 CARNE"], 3)

        assert "Almoço 29.04.2026 -> Pedidos da NETSUL" in corpo
        assert "02 FRANGO\n01 CARNE" in corpo
        assert "Total de *03 Marmitas*" in corpo


class TestLinksWhatsApp:
    def test_wpp_valido_gera_url_correta(self):
        link = montar_link_whatsapp("5511999999999", "Teste")
        assert link is not None
        assert "wa.me/5511999999999" in link
        assert urllib.parse.unquote(link.split("text=", 1)[1]) == "Teste"

    def test_wpp_invalido_retorna_none(self):
        assert montar_link_whatsapp("123456", "Teste") is None


class TestCobrancaPix:
    def test_gera_link_cobranca_quando_config_completa(self):
        link = montar_link_cobranca(
            total_marmitas=3,
            numero_chef="5511988887777",
            chave_pix="pix@example.com",
            nome_pix="IARA SANTANA",
            valor_marmita=18,
        )

        assert link is not None
        assert link.startswith("https://wa.me/5511988887777?text=")
        mensagem = urllib.parse.unquote(link.split("text=", 1)[1])
        assert "Total a pagar: 3 x R$ 18 = R$ 54" in mensagem
        assert "PIX: pix@example.com (IARA SANTANA)" in mensagem

    def test_nao_gera_cobranca_sem_numero_chef(self):
        assert montar_link_cobranca(3, "", "pix@example.com", "IARA SANTANA", 18) is None

    def test_nao_gera_cobranca_sem_chave_pix(self):
        assert montar_link_cobranca(3, "5511988887777", "", "IARA SANTANA", 18) is None


class TestUsuariosCommand:
    def test_monta_lista_usuarios_ativos_e_nao_ativos(self):
        config = {
            "usuarios_cadastrados": {
                "111": {"nome": "Ana", "monitorar": True},
                "222": {"nome": "Bruno", "monitorar": False},
            },
            "usuarios_monitoramento": [111],
        }

        result = main.montar_lista_usuarios(config)

        assert "**Ativos (1):**" in result
        assert "**Nao ativos (1):**" in result
        assert "<@111> - Ana (`111`)" in result
        assert "<@222> - Bruno (`222`)" in result

    def test_monta_lista_usuarios_config_antigo(self):
        result = main.montar_lista_usuarios({"usuarios_monitoramento": [111]})

        assert "**Ativos (1):**" in result
        assert "<@111> - Usuario 111 (`111`)" in result
        assert "**Nao ativos (0):**" in result

    def test_monta_lista_usuarios_vazio(self):
        result = main.montar_lista_usuarios({})

        assert "Nenhum usuario cadastrado" in result


class TestCompatibilidadeMain:
    def test_main_mantem_funcoes_usadas_por_bot_py(self):
        assert main.validar_numero_whatsapp("5511999999999") == "5511999999999"
        assert main.montar_linha_prato("FRANGO", 1, {}, True) == "01 FRANGO"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
