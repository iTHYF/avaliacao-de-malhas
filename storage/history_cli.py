import os
import shutil
from uuid import uuid4

from storage.history_identity import RAIZ_PROJETO
from storage.history_query_service import HistoryQueryService


def consultar_historico():

    print("\n========== HISTORICO DE AVALIACOES ==========")
    print("Informe os dados registrados na simulacao.\n")

    responsavel = input(
        "Engenheiro responsavel: "
    ).strip()

    nome_malha = input(
        "Nome da malha: "
    ).strip()

    try:
        K = float(
            input("Ganho K da planta: ").replace(",", ".")
        )

        tau = float(
            input("Constante de tempo tau: ").replace(",", ".")
        )

        T = float(
            input("Atraso T: ").replace(",", ".")
        )

        servico = HistoryQueryService()

        origem = servico.arquivo_validado(
            responsavel,
            nome_malha,
            K,
            tau,
            T
        )

    except (ValueError, OSError, RuntimeError) as erro:
        print(f"\n[ERRO] {erro}")
        return

    if origem is None:
        print(
            "\nNenhum historico encontrado para "
            "essa combinacao de dados."
        )
        return

    print("\nHistorico encontrado!")
    print(f"Arquivo: {origem.name}")

    while True:

        print("\n========== OPCOES DO HISTORICO ==========")
        print("[1] Abrir planilha no Excel")
        print("[2] Exportar copia da planilha")
        print("[3] Listar avaliacoes registradas")
        print("[0] Voltar ao menu principal")

        opcao = input("\nEscolha uma opcao: ").strip()

        if opcao == "0":
            return

        elif opcao == "1":
            try:
                if os.name == "nt":
                    os.startfile(str(origem))
                else:
                    print(f"Planilha localizada em: {origem}")

            except OSError as erro:
                print(f"[ERRO] Falha ao abrir Excel: {erro}")

        elif opcao == "2":
            try:
                pasta = RAIZ_PROJETO / "exportacoes"
                pasta.mkdir(parents=True, exist_ok=True)

                destino = pasta / (
                    f"{origem.stem}_"
                    f"{uuid4().hex[:8]}.xlsx"
                )

                shutil.copy2(origem, destino)

                print("\nPlanilha exportada com sucesso!")
                print(f"Local: {destino}")

            except OSError as erro:
                print(f"[ERRO] Falha na exportacao: {erro}")

        elif opcao == "3":
            try:
                avaliacoes = servico.listar_avaliacoes(
                    responsavel,
                    nome_malha,
                    K,
                    tau,
                    T
                )

                if not avaliacoes:
                    print("\nNenhuma avaliacao registrada.")
                    continue

                print("\nAVALIACOES REGISTRADAS")

                for i, avaliacao in enumerate(
                    avaliacoes, start=1
                ):
                    print(
                        f"\n{i}. "
                        f"Data: {avaliacao['data_hora']}"
                        f"\n   ID: {avaliacao['id_avaliacao']}"
                        f"\n   Controladores: "
                        f"{avaliacao['quantidade_controladores']}"
                    )

            except (ValueError, OSError, RuntimeError) as erro:
                print(f"[ERRO] {erro}")

        else:
            print("Opcao invalida.")
