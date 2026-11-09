"""Testes isolados: nenhum ADC real ou acesso à rede/planilha."""
import copy
import unittest
from unittest.mock import Mock, patch

import catalogo
import leitor_sheets as leitor


class CredencialVinculada:
    """Dublê local; não consulta metadata nem autentica."""
    def __init__(self):
        self.valid = True
        self.token = 'token-exclusivamente-ficticio'
        self.service_account_email = leitor.IDENTIDADE_LIA
        self.refresh = Mock()


class LeitorSheetsTests(unittest.TestCase):
    def dados(self, *linhas):
        return {'majorDimension': 'ROWS', 'values': [list(catalogo.COLUNAS), *linhas]}

    def consultar(self, dados, status=200):
        sessao = Mock()
        sessao.get.return_value.status_code = status
        sessao.get.return_value.json.return_value = dados
        with patch.object(leitor, '_criar_sessao', return_value=sessao):
            resultado = leitor.ler_catalogo('Catálogo')
        sessao.close.assert_called_once_with()
        return resultado, sessao

    def test_adc_solicita_exclusivamente_escopo_leitura(self):
        auth, construtor, requisicao = Mock(), Mock(), Mock()
        credenciais = CredencialVinculada()
        auth.default.return_value = (credenciais, 'projeto')
        with patch.object(leitor, '_dependencias', return_value=(
                auth, CredencialVinculada, construtor, requisicao)):
            self.assertIsInstance(leitor._criar_sessao(20), leitor._SessaoLia)
        auth.default.assert_called_once_with(scopes=(
            'https://www.googleapis.com/auth/spreadsheets.readonly',))
        construtor.assert_called_once_with()
        requisicao.assert_called_once_with(session=construtor.return_value)

    def test_rejeita_adc_de_chave_privada(self):
        self.rejeitar_tipo_adc(object())

    def rejeitar_tipo_adc(self, credenciais):
        auth, construtor = Mock(), Mock()
        auth.default.return_value = (credenciais, 'projeto')
        with patch.object(leitor, '_dependencias', return_value=(
                auth, CredencialVinculada, construtor, Mock())):
            with self.assertRaises(leitor.ErroAutenticacaoSheets):
                leitor._criar_sessao(20)
        construtor.assert_not_called()

    def test_rejeita_adc_usuario_mesmo_com_email_da_lia(self):
        usuario = Mock(service_account_email=leitor.IDENTIDADE_LIA)
        self.rejeitar_tipo_adc(usuario)

    def test_adc_ausente_erro_sem_vazar_detalhes(self):
        auth = Mock()
        auth.default.side_effect = RuntimeError('segredo-ficticio')
        with patch.object(leitor, '_dependencias', return_value=(
                auth, CredencialVinculada, Mock(), Mock())):
            with self.assertRaises(leitor.ErroAutenticacaoSheets) as erro:
                leitor._criar_sessao(20)
        self.assertNotIn('segredo-ficticio', str(erro.exception))

    def test_leitura_do_id_oficial_somente_get(self):
        _, sessao = self.consultar(self.dados())
        chamada = sessao.get.call_args
        self.assertIn('/' + leitor.PLANILHA_ID + '/values/', chamada.args[0])
        self.assertTrue(chamada.args[0].endswith('%27Cat%C3%A1logo%27%21A1%3AL'))
        self.assertEqual(chamada.kwargs, {
            'params': {'majorDimension': 'ROWS', 'valueRenderOption': 'FORMATTED_VALUE'},
            'timeout': 20, 'allow_redirects': False})
        self.assertEqual([c[0] for c in sessao.method_calls], ['get', 'close'])

    def test_escapa_nome_da_aba(self):
        sessao = Mock()
        sessao.get.return_value.status_code = 200
        sessao.get.return_value.json.return_value = self.dados()
        with patch.object(leitor, '_criar_sessao', return_value=sessao):
            leitor.ler_catalogo("Lia d'água")
        self.assertIn('d%27%27%C3%A1gua', sessao.get.call_args.args[0])

    def test_doze_campos_e_pesquisa_oficial(self):
        linha = ['FIC-108', 'Jogo fictício', 'criação', 'Gênesis 1:1',
                 '4 a 8 anos', 'jogo', '', 'Publicado', '',
                 'https://example.invalid/108']
        resultado, _ = self.consultar(self.dados(linha))
        self.assertEqual(set(resultado[0]), set(catalogo.COLUNAS))
        self.assertEqual(resultado[0]['Data de publicação'], '')
        self.assertEqual(catalogo.pesquisar(resultado, tema='criação',
                         faixa_etaria='6 anos', tipo='jogo'), resultado)

    def test_celulas_vazias_interiores_e_finais(self):
        resultado, _ = self.consultar(self.dados(['FIC', None, '', ' ']))
        self.assertEqual(resultado[0]['Título do material'], '')
        self.assertEqual(resultado[0]['Referência bíblica'], ' ')
        self.assertEqual(resultado[0]['Link do arquivo'], '')

    def test_linhas_totalmente_vazias_ignoradas(self):
        resultado, _ = self.consultar(self.dados([], ['', None, '  ']))
        self.assertEqual(resultado, [])

    def test_so_cabecalho_e_catalogo_vazio_valido(self):
        self.assertEqual(self.consultar(self.dados())[0], [])

    def test_ausencia_de_cabecalho_nao_e_lista_vazia(self):
        for dados in ({}, {'majorDimension': 'ROWS'},
                      {'majorDimension': 'ROWS', 'values': []}):
            with self.subTest(dados=dados):
                with self.assertRaises(leitor.ErroEstruturaSheets):
                    self.consultar(dados)

    def test_cabecalhos_incorretos_rejeitados(self):
        for cabecalho in (list(catalogo.COLUNAS)[::-1],
                          list(catalogo.COLUNAS)[:-1], ['Código'] * 12):
            with self.subTest(cabecalho=cabecalho):
                with self.assertRaises(leitor.ErroEstruturaSheets):
                    self.consultar({'majorDimension': 'ROWS', 'values': [cabecalho]})

    def test_estrutura_malformada(self):
        for dados in ([], self.dados('linha'), self.dados(['x'] * 13),
                      self.dados([1]), self.dados([True]),
                      {'majorDimension': 'COLUMNS', 'values': []}):
            with self.subTest(dados=dados):
                with self.assertRaises(leitor.ErroEstruturaSheets):
                    self.consultar(dados)

    def test_erros_http_nunca_retornam_lista_vazia(self):
        for status in (301, 400, 401, 403, 404, 429, 500, 503):
            with self.subTest(status=status):
                with self.assertRaises(leitor.ErroLeituraSheets) as erro:
                    self.consultar(self.dados(), status)
                self.assertIn(str(status), str(erro.exception))

    def test_acesso_negado_e_falha_clara_de_autenticacao(self):
        for status in (401, 403):
            with self.subTest(status=status):
                with self.assertRaises(leitor.ErroAutenticacaoSheets) as erro:
                    self.consultar(self.dados(), status)
                self.assertIn('não foi possível confirmar o acesso de leitura da Lia',
                              str(erro.exception))

    def test_timeout_e_conexao_fecham_sessao(self):
        for falha in (TimeoutError(), ConnectionError(), RuntimeError('token-ficticio')):
            sessao = Mock()
            sessao.get.side_effect = falha
            with patch.object(leitor, '_criar_sessao', return_value=sessao):
                with self.assertRaises(leitor.ErroLeituraSheets) as erro:
                    leitor.ler_catalogo('Catálogo')
            self.assertNotIn('token-ficticio', str(erro.exception))
            sessao.close.assert_called_once()

    def test_json_invalido(self):
        sessao = Mock()
        sessao.get.return_value.status_code = 200
        sessao.get.return_value.json.side_effect = ValueError()
        with patch.object(leitor, '_criar_sessao', return_value=sessao):
            with self.assertRaises(leitor.ErroEstruturaSheets):
                leitor.ler_catalogo('Catálogo')
        sessao.close.assert_called_once()

    def test_validacao_antes_de_autenticar(self):
        with patch.object(leitor, '_criar_sessao') as criar:
            for aba in ('', ' ', None, 3):
                with self.assertRaises(ValueError):
                    leitor.ler_catalogo(aba)
            for timeout in (0, -1, True, '20', float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    leitor.ler_catalogo('Catálogo', timeout=timeout)
            criar.assert_not_called()

    def test_nao_muda_status_nem_dados_recebidos(self):
        dados = self.dados(['FIC'], ['OUTRO', '', '', '', '', '', '', 'Rascunho'])
        antes = copy.deepcopy(dados)
        resultado, _ = self.consultar(dados)
        self.assertEqual(dados, antes)
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[1]['Status'], 'Rascunho')


class IdentidadeLiaTests(unittest.TestCase):
    def setUp(self):
        self.credenciais = CredencialVinculada()
        self.http = Mock()
        self.info = {'scope': leitor.ESCOPOS[0], 'expires_in': '3600'}
        self.http.post.return_value.status_code = 200
        self.http.post.return_value.json.return_value = self.info
        self.sessao = leitor._SessaoLia(self.credenciais, self.http, Mock(), 20)
        self.url = ('https://sheets.googleapis.com/v4/spreadsheets/'
                    + leitor.PLANILHA_ID + '/values/range')

    def ler(self):
        return self.sessao.get(self.url, params={}, timeout=20, allow_redirects=False)

    def bloqueado(self):
        with self.assertRaises(leitor.ErroAutenticacaoSheets) as erro:
            self.ler()
        self.assertNotIn(self.credenciais.token or 'segredo-ficticio', str(erro.exception))
        self.assertFalse(any(c.args[0].startswith('https://sheets.googleapis.com')
                             for c in self.http.get.call_args_list))

    def test_identidade_e_escopo_corretos_enviam_token_inspecionado(self):
        self.ler()
        primeira, segunda = self.http.post.call_args, self.http.get.call_args
        self.assertEqual(primeira.args, ('https://www.googleapis.com/oauth2/v1/tokeninfo',))
        self.assertNotIn('params', primeira.kwargs)
        self.assertEqual(primeira.kwargs['data'], {'access_token': self.credenciais.token})
        self.assertNotIn(self.credenciais.token, primeira.args[0])
        self.assertEqual(segunda.kwargs['headers'], {
            'Authorization': 'Bearer ' + self.credenciais.token})
        self.assertFalse(segunda.kwargs['allow_redirects'])

    def test_identidade_metadata_incorreta(self):
        self.credenciais.service_account_email = 'outra@example.invalid'
        self.bloqueado()
        self.http.get.assert_not_called()

    def test_identidade_metadata_nao_confirmada(self):
        self.credenciais.service_account_email = 'default'
        self.bloqueado()

    def test_email_tokeninfo_nao_e_fonte_de_identidade(self):
        self.info['email'] = 'campo-nao-utilizado@example.invalid'
        self.ler()
        self.http.get.assert_called_once()

    def test_token_sem_campo_email_e_aceito(self):
        self.assertNotIn('email', self.info)
        self.ler()
        self.http.get.assert_called_once()

    def test_escopo_amplo_rejeitado(self):
        self.info['scope'] += ' https://www.googleapis.com/auth/cloud-platform'
        self.bloqueado()

    def test_escopo_escrita_rejeitado(self):
        self.info['scope'] = 'https://www.googleapis.com/auth/spreadsheets'
        self.bloqueado()

    def test_escopo_ausente_rejeitado(self):
        del self.info['scope']
        self.bloqueado()

    def test_token_expirado_rejeitado(self):
        self.info['expires_in'] = '0'
        self.bloqueado()

    def test_validade_desconhecida_rejeitada(self):
        del self.info['expires_in']
        self.bloqueado()

    def test_token_ausente(self):
        self.credenciais.token = None
        self.bloqueado()

    def test_inspecao_indisponivel(self):
        self.http.post.side_effect = TimeoutError('segredo-ficticio')
        self.bloqueado()

    def test_inspecao_http_erro(self):
        self.http.post.return_value.status_code = 403
        self.bloqueado()

    def test_inspecao_resposta_invalida(self):
        self.http.post.return_value.json.side_effect = ValueError('segredo-ficticio')
        self.bloqueado()

    def test_renovacao_verifica_novo_token(self):
        self.credenciais.valid = False
        def renovar(request):
            self.credenciais.token = 'novo-token-ficticio'
            self.credenciais.valid = True
            request(url='https://metadata.invalid', method='GET')
        self.credenciais.refresh.side_effect = renovar
        self.ler()
        self.credenciais.refresh.assert_called_once()
        self.sessao._requisicao.assert_called_once_with(
            url='https://metadata.invalid', method='GET', timeout=20)
        self.assertEqual(self.http.get.call_args.kwargs['headers'], {
            'Authorization': 'Bearer novo-token-ficticio'})

    def test_renovacao_falha_sem_expor_detalhes(self):
        self.credenciais.valid = False
        self.credenciais.refresh.side_effect = RuntimeError('segredo-ficticio')
        self.bloqueado()
        self.http.get.assert_not_called()

    def test_revalida_a_cada_leitura(self):
        self.ler()
        self.http.reset_mock()
        self.info['scope'] += ' https://www.googleapis.com/auth/drive'
        self.bloqueado()

    def test_identidade_resolvida_somente_apos_renovacao(self):
        self.credenciais.service_account_email = 'default'
        def renovar(request):
            self.credenciais.service_account_email = leitor.IDENTIDADE_LIA
        self.credenciais.refresh.side_effect = renovar
        self.ler()
        self.credenciais.refresh.assert_called_once()
        self.http.get.assert_called_once()

    def test_renovacao_pode_revelar_identidade_incorreta(self):
        def renovar(request):
            self.credenciais.service_account_email = 'outra@example.invalid'
        self.credenciais.refresh.side_effect = renovar
        self.bloqueado()
        self.http.post.assert_not_called()

    def test_credencial_invalida_apos_renovacao(self):
        self.credenciais.valid = False
        self.bloqueado()
        self.http.post.assert_not_called()

    def test_resposta_de_inspecao_sem_estrutura(self):
        self.http.post.return_value.json.return_value = []
        self.bloqueado()

    def test_validade_malformada(self):
        self.info['expires_in'] = 'segredo-ficticio'
        self.bloqueado()

    def test_sem_envio_a_destino_alternativo(self):
        self.url = 'https://example.invalid'
        self.bloqueado()


if __name__ == '__main__':
    unittest.main()
