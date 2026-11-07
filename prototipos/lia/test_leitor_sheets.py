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
