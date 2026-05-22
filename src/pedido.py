def montar_linha_prato(
    prato: str,
    qtd: int,
    votos_por_usuario: dict,
    preferencias_sem: dict,
    tem_macarrao: bool = True,
) -> str:
    usuarios_com_restricao = []

    for user_id, restricao in preferencias_sem.items():
        if prato in votos_por_usuario.get(user_id, []) and tem_macarrao:
            usuarios_com_restricao.append(restricao)

    qtd_sem = len(usuarios_com_restricao)

    if qtd_sem == 0:
        return f"{qtd:02d} {prato}"

    obs_texto = " / ".join(set(usuarios_com_restricao))

    if qtd_sem == qtd:
        return f"{qtd:02d} {prato} (SEM {obs_texto})"
    return f"{qtd:02d} {prato} ({qtd_sem:02d} SEM {obs_texto})"


def montar_corpo_pedido(hoje: str, lista_formatada: list[str], total_marmitas: int) -> str:
    return (
        "---------------------------------------------------\n"
        f"Almoço {hoje} -> Pedidos da NETSUL\n"
        "---------------------------------------------------\n\n"
        "*--------MARMITAS TAMANHO M---------*\n\n"
        + "\n".join(lista_formatada) +
        "\n\n---------------------------------------------------\n"
        f"Entregar na *NETSUL* -> Total de *{total_marmitas:02d} Marmitas*\n"
        "RUA DR. CICERO ROSA 589, BAIRRO SAUDE\n"
        "---------------------------------------------------"
    )
