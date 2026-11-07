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
        return self._http.get(
            url, params=params, timeout=timeout, allow_redirects=False,
            headers={'Authorization': 'Bearer ' + token})

    def close(self):
        self._http.close()


def _criar_sessao(timeout):
    auth, credencial_vinculada, sessao_http, requisicao = _dependencias()
    try:
        credenciais, _ = auth.default(scopes=ESCOPOS)
        if not isinstance(credenciais, credencial_vinculada):
            raise ErroAutenticacaoSheets(
                'ADC não permitida: use a identidade vinculada da conta de serviço da Lia; '
                'credenciais locais de usuário e chaves privadas são rejeitadas.')
        http = sessao_http()
        try:
            return _SessaoLia(credenciais, http, requisicao(session=http), timeout)
        except Exception:
            http.close()
            raise
    except ErroAutenticacaoSheets:
        raise
    except Exception:
        # Não expõe conteúdo de credenciais, tokens ou mensagens do provedor.
        raise ErroAutenticacaoSheets('Não foi possível obter a identidade vinculada da Lia via ADC.') from None


def _converter(resposta):
    if not isinstance(resposta, dict) or resposta.get('majorDimension') != 'ROWS':
        raise ErroEstruturaSheets('Resposta inválida: esperadas linhas da Sheets API.')
    linhas = resposta.get('values')
    if not isinstance(linhas, list) or not linhas:
        raise ErroEstruturaSheets('Cabeçalho do catálogo ausente.')
    if linhas[0] != list(COLUNAS):
        raise ErroEstruturaSheets('Cabeçalho diferente das 12 colunas oficiais na ordem prevista.')
    materiais = []
    for linha in linhas[1:]:
        if not isinstance(linha, list) or len(linha) > len(COLUNAS):
            raise ErroEstruturaSheets('Linha incompatível com as 12 colunas oficiais.')
        # FORMATTED_VALUE retorna textos; None também é tratado como célula vazia.
        if any(v is not None and not isinstance(v, str) for v in linha):
            raise ErroEstruturaSheets('Esperados valores textuais formatados.')
        valores = ['' if v is None else v for v in linha]
        valores += [''] * (len(COLUNAS) - len(valores))
        if any(v.strip() for v in valores):
            materiais.append(dict(zip(COLUNAS, valores)))
    return materiais


def ler_catalogo(aba, *, timeout=20):
    """Lê A1:L da aba explícita do catálogo oficial usando exclusivamente GET.

    Retorna todos os registros, inclusive rascunhos e incompletos, para o
    catálogo aplicar suas regras. [] exige cabeçalho válido e leitura bem-sucedida
    sem linhas preenchidas. Qualquer falha levanta ErroLeituraSheets ou subclasse.
    Não acessa links, não registra pedidos, não entrega e não altera a planilha.
    """
    if not isinstance(aba, str) or not aba.strip():
        raise ValueError('Informe o nome exato da aba do catálogo.')
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('timeout deve ser um número positivo finito em segundos.')
    intervalo = "'" + aba.replace("'", "''") + "'!A1:L"
    url = ('https://sheets.googleapis.com/v4/spreadsheets/' + PLANILHA_ID
           + '/values/' + quote(intervalo, safe=''))
    sessao = _criar_sessao(timeout)
    try:
        resposta = sessao.get(
            url, params={'majorDimension': 'ROWS', 'valueRenderOption': 'FORMATTED_VALUE'},
            timeout=timeout, allow_redirects=False)
        if resposta.status_code in (401, 403):
            raise ErroAutenticacaoSheets(
                f'Consulta não autorizada (HTTP {resposta.status_code}); '
                'não foi possível confirmar o acesso de leitura da Lia ao catálogo.')
        if resposta.status_code != 200:
            raise ErroLeituraSheets(
                f'Consulta não concluída (HTTP {resposta.status_code}); '
                'não é possível concluir se há materiais.')
        try:
            dados = resposta.json()
        except Exception:
            raise ErroEstruturaSheets('A Sheets API retornou uma resposta JSON inválida.') from None
        return _converter(dados)
    except ErroLeituraSheets:
        raise
    except Exception:
        raise ErroLeituraSheets(
            'Falha de conexão ou autenticação durante a consulta; '
            'não é possível concluir se há materiais.') from None
    finally:
        sessao.close()
