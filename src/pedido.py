import unicodedata


def _sem_acento(text: str) -> str:
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('ascii')


def montar_linha_prato(
    prato: str,
    qtd: int,
    votos_por_usuario: dict,
    preferencias_sem: dict,
    tem_macarrao: bool = True,
    extra_restricoes: dict[str, int] | None = None,
) -> str:
    counter: dict[str, int] = {}
    for user_id, restricao in preferencias_sem.items():
        if prato in votos_por_usuario.get(user_id, []) and tem_macarrao:
            counter[restricao] = counter.get(restricao, 0) + 1

    if extra_restricoes:
        for restricao, count in extra_restricoes.items():
            nk = _sem_acento(restricao.upper().strip())
            found = False
            for ek in list(counter.keys()):
                if _sem_acento(ek.upper()) == nk:
                    counter[ek] += count
                    found = True
                    break
            if not found:
                counter[restricao.upper().strip()] = count

    if not counter:
        return f"{qtd:02d} {prato}"

    partes = [f"{c:02d} SEM {k}" for k, c in sorted(counter.items())]
    return f"{qtd:02d} {prato} ({' / '.join(partes)})"


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
