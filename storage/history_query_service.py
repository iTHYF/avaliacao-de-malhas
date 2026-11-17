from datetime import date, datetime
import math

import pandas as pd

from storage.history_identity import caminho_historico


class HistoryQueryService:

    def caminho(self, responsavel, nome_malha, K, tau, T):
        arquivo = caminho_historico(
            responsavel, nome_malha, K, tau, T
        )
        return arquivo if arquivo.is_file() else None

    @staticmethod
    def _valor(valor):
        if valor is None:
            return None

        if isinstance(valor, (datetime, date, pd.Timestamp)):
            return valor.isoformat()

        try:
            if pd.isna(valor):
                return None
        except (ValueError, TypeError):
            pass

        if hasattr(valor, "item") and not isinstance(
            valor, (str, bytes)
        ):
            valor = valor.item()

        if isinstance(valor, float) and not math.isfinite(valor):
            return None

        return valor

    @classmethod
    def _linhas(cls, dados):
        if dados is None or dados.empty:
            return []

        return [
            {
                str(coluna): cls._valor(valor)
                for coluna, valor in linha.items()
            }
            for linha in dados.to_dict(orient="records")
        ]

    @staticmethod
    def _filtrar(df, id_avaliacao):
        if df is None or "ID_Avaliacao" not in df.columns:
            return None

        return df.loc[
            df["ID_Avaliacao"].astype(str)
            == str(id_avaliacao)
        ]

    def _ler_grupo(self, responsavel, nome_malha, K, tau, T):
        arquivo = self.caminho(
            responsavel, nome_malha, K, tau, T
        )

        if arquivo is None:
            return None, None

        try:
            abas = pd.read_excel(
                arquivo, sheet_name=None
            )
        except Exception as exc:
            raise RuntimeError(
                f"Falha ao ler o historico: {exc}"
            ) from exc

        avaliacoes = abas.get("Avaliacoes")

        if avaliacoes is None:
            raise ValueError(
                "Planilha sem a aba Avaliacoes."
            )

        if not {
            "ID_Avaliacao",
            "Nome_Malha",
            "Responsavel"
        }.issubset(avaliacoes.columns):
            raise ValueError(
                "Planilha com campos de identificacao ausentes."
            )

        # Confere se todas as avaliacoes pertencem ao grupo.
        for registro in self._linhas(avaliacoes):
            responsavel_salvo = str(
                registro.get("Responsavel") or ""
            ).strip()

            malha_salva = str(
                registro.get("Nome_Malha") or ""
            ).strip()

            if (
                responsavel_salvo != str(responsavel).strip()
                or malha_salva != str(nome_malha).strip()
            ):
                raise ValueError(
                    "O arquivo contem registros de outro "
                    "responsavel ou de outra malha."
                )

        return arquivo, abas

    def arquivo_validado(
        self, responsavel, nome_malha, K, tau, T
    ):
        arquivo, _ = self._ler_grupo(
            responsavel, nome_malha, K, tau, T
        )
        return arquivo

    def listar_avaliacoes(
        self, responsavel, nome_malha, K, tau, T
    ):
        _, abas = self._ler_grupo(
            responsavel, nome_malha, K, tau, T
        )

        if abas is None:
            return []

        controladores = abas.get("Controladores")
        resultado = []

        for registro in self._linhas(abas["Avaliacoes"]):
            id_avaliacao = registro["ID_Avaliacao"]

            vinculados = self._filtrar(
                controladores, id_avaliacao
            )

            resultado.append({
                "id_avaliacao": str(id_avaliacao),
                "data_hora": registro.get("Data_Hora"),
                "nome_malha": registro.get("Nome_Malha"),
                "responsavel": registro.get("Responsavel"),
                "quantidade_controladores": (
                    len(vinculados)
                    if vinculados is not None else 0
                )
            })

        resultado.sort(
            key=lambda item: str(
                item["data_hora"] or ""
            ),
            reverse=True
        )

        return resultado

    def obter_avaliacao(
        self, id_avaliacao,
        responsavel, nome_malha, K, tau, T
    ):
        _, abas = self._ler_grupo(
            responsavel, nome_malha, K, tau, T
        )

        if abas is None:
            return None

        avaliacao = self._linhas(
            self._filtrar(
                abas.get("Avaliacoes"), id_avaliacao
            )
        )

        if not avaliacao:
            return None

        ensaios = self._linhas(
            self._filtrar(
                abas.get("Ensaios"), id_avaliacao
            )
        )

        controladores = self._linhas(
            self._filtrar(
                abas.get("Controladores"), id_avaliacao
            )
        )

        metricas = self._linhas(
            self._filtrar(
                abas.get("Metricas"), id_avaliacao
            )
        )

        pesos = self._linhas(
            self._filtrar(
                abas.get("Pesos"), id_avaliacao
            )
        )

        for controlador in controladores:
            controlador["metricas"] = [
                metrica
                for metrica in metricas
                if str(metrica.get("ID_Controlador"))
                == str(controlador.get("ID_Controlador"))
            ]

        return {
            "avaliacao": avaliacao[0],
            "ensaios": ensaios,
            "controladores": controladores,
            "pesos": pesos
        }
