"""Etapa 108: leitura da Sheets API via ADC, sem escrita ou chave privada."""
import math
from urllib.parse import quote

from catalogo import COLUNAS

PLANILHA_ID = '1NHDv3qSNqsfSyOh6f3t94y3Xq_2M6Xs6BZXU6XHEAA0'
ESCOPOS = ('https://www.googleapis.com/auth/spreadsheets.readonly',)
IDENTIDADE_LIA = 'lia-kingdom-kids@kingdom-kids-lab.iam.gserviceaccount.com'


class ErroLeituraSheets(RuntimeError):
    """Consulta não concluída: nunca equivale a catálogo vazio."""


class ErroAutenticacaoSheets(ErroLeituraSheets):
    """ADC ausente, inválida ou incompatível com a política sem chaves."""


class ErroEstruturaSheets(ErroLeituraSheets):
    """Resposta ou cabeçalhos incompatíveis com o catálogo oficial."""


def _dependencias():
    # Apenas identidade vinculada: ADC de usuário, chave e federação direta
    # não são aceitas nesta versão. Nenhum login é iniciado pelo módulo.
    try:
        import google.auth
        from google.auth.compute_engine import Credentials
        from google.auth.transport.requests import Request
        from requests import Session
    except ImportError:
        raise ErroAutenticacaoSheets(
            'Instale google-auth e requests para a leitura autenticada.') from None
    return google.auth, Credentials, Session, Request


class _SessaoLia:
    """Envia somente o token cuja identidade e escopos foram confirmados.

    Não usa AuthorizedSession: uma renovação automática posterior à validação
    poderia trocar o token sem verificar novamente suas permissões efetivas.
    """

    def __init__(self, credenciais, http, requisicao, timeout):
        self._credenciais = credenciais
        self._http = http
        self._requisicao = requisicao
        self._timeout = timeout

    def get(self, url, *, params, timeout, allow_redirects):
        try:
            credenciais = self._credenciais
            # Sempre atualiza antes de conferir service_account_email: o valor
            # inicial pode ser apenas o alias "default", ainda não resolvido.
            def requisicao(*args, **kwargs):
                kwargs['timeout'] = self._timeout
                return self._requisicao(*args, **kwargs)
            credenciais.refresh(requisicao)
            if not credenciais.valid:
                raise ErroAutenticacaoSheets('As credenciais atualizadas da Lia não são válidas.')
            token = credenciais.token
            if not isinstance(token, str) or not token:
                raise ErroAutenticacaoSheets('Não foi possível confirmar o token da Lia.')
            if credenciais.service_account_email != IDENTIDADE_LIA:
                raise ErroAutenticacaoSheets('A identidade vinculada não é a conta exclusiva da Lia.')
            # Inspeção somente de escopo e validade, nunca de identidade.
            # POST documentado pelo Google evita o token na URL. É mantido
            # porque apenas pedir scopes não comprova os escopos emitidos.
            info = self._http.post(
                'https://www.googleapis.com/oauth2/v1/tokeninfo',
                data={'access_token': token}, timeout=self._timeout,
                allow_redirects=False)
            if info.status_code != 200:
                raise ErroAutenticacaoSheets('Não foi possível confirmar validade e escopos do token.')
            dados = info.json()
            if not isinstance(dados, dict):
                raise ErroAutenticacaoSheets('Resposta inválida na verificação de escopos e validade.')
            escopos = dados.get('scope')
            if not isinstance(escopos, str) or set(escopos.split()) != set(ESCOPOS):
                raise ErroAutenticacaoSheets(
                    'Permissões do token não confirmadas: exigido somente spreadsheets.readonly.')
            validade = dados.get('expires_in')
            if (isinstance(validade, bool) or not isinstance(validade, (str, int))
                    or int(validade) <= 0):
                raise ErroAutenticacaoSheets('Não foi possível confirmar a validade do token.')
        except ErroAutenticacaoSheets:
            raise
        except Exception:
            raise ErroAutenticacaoSheets(
                'Não foi possível confirmar a identidade e as permissões efetivas da Lia.') from None
        # Usa exatamente a string inspecionada. Não há renovação automática,
        # fallback para usuário nem envio do token para outros destinos.
        destino = 'https://sheets.googleapis.com/v4/spreadsheets/' + PLANILHA_ID + '/values/'
        if not url.startswith(destino) or allow_redirects is not False:
            raise ErroAutenticacaoSheets('Destino de leitura não autorizado.')
