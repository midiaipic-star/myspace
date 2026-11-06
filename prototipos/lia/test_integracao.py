"""Testes do fluxo integrado, sem rede e com fixtures fictícias."""
import copy
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import catalogo
import integracao as fluxo
from lia import Pedido


class IntegracaoTests(unittest.TestCase):
    def pedido(self, tema='criação', idade='6 anos', tipo='jogo'):
        return Pedido.receber(f'tema: {tema}; faixa etária: {idade}; tipo: {tipo}')

    def executar(self, entradas):
        saida = io.StringIO()
        with patch('builtins.input', side_effect=entradas), redirect_stdout(saida):
            fluxo.main()
        return saida.getvalue()

    def test_publicados_completos_e_incompletos(self):
        resultado = fluxo.consultar(self.pedido())
        self.assertEqual(resultado['total_encontrado'], 2)
        self.assertEqual([m['codigo'] for m in resultado['materiais']], ['FIC-001'])
        self.assertEqual(resultado['pendencias'][0]['campos_pendentes'], ['Link do arquivo'])

    def test_campos_essenciais_bloqueiam_secundarios_geram_pendencias(self):
        for coluna in catalogo.COLUNAS:
            # Campos de filtro vazios não correspondem à pesquisa; demais
            # campos ausentes precisam aparecer como pendência administrativa.
            if coluna in ('Tema bíblico', 'Faixa etária', 'Tipo de material', 'Status'):
                continue
            with self.subTest(coluna=coluna):
                dados = fluxo.materiais_ficticios()[:1]
                dados[0][coluna] = '  '
                with patch.object(fluxo, 'materiais_ficticios', return_value=dados):
                    resultado = fluxo.consultar(self.pedido())
                if coluna in ('Código', 'Título do material', 'Link do arquivo'):
                    self.assertEqual(resultado['materiais'], [])
                else:
                    self.assertEqual(len(resultado['materiais']), 1)
                    self.assertFalse(resultado['materiais'][0]['cadastro_completo'])
                self.assertIn(coluna, resultado['pendencias'][0]['campos_pendentes'])

    def test_sem_correspondencia(self):
        pedido = self.pedido(tema='oração')
        texto = fluxo.apresentar_resultado(pedido, fluxo.consultar(pedido))
        self.assertIn('Não foi encontrado material publicado correspondente entre os registros consultados.', texto)
        self.assertNotIn('não existe', texto)

    def test_filtros_combinados_e_cobertura_total(self):
        for pedido in (self.pedido(idade='9 anos'), self.pedido(idade='3 a 6 anos'),
                       self.pedido(tipo='aula')):
            self.assertEqual(fluxo.consultar(pedido)['total_encontrado'], 0)

    def test_plural_e_idade_da_lia(self):
        self.assertEqual(fluxo.consultar(self.pedido(idade='dos 4 a 6 anos', tipo='jogos'))['total_encontrado'], 2)

    def test_pedido_incompleto_nao_pesquisa(self):
        with patch.object(catalogo, 'pesquisar') as pesquisa:
            with self.assertRaises(ValueError):
                fluxo.consultar(Pedido.receber(''))
            pesquisa.assert_not_called()

    def test_dados_preservados(self):
        dados = fluxo.materiais_ficticios()
        antes = copy.deepcopy(dados)
        with patch.object(fluxo, 'materiais_ficticios', return_value=dados):
            fluxo.consultar(self.pedido())
        self.assertEqual(dados, antes)

    def test_terminal_texto_livre(self):
        texto = self.executar(['Quero jogos sobre criação para crianças de 6 anos.'])
        self.assertIn('Publicado com cadastro completo: FIC-001', texto)
        self.assertIn('Necessidade de correção administrativa', texto)
        self.assertNotIn('FIC-003', texto)
        self.assertIn('Links não foram acessados nem verificados.', texto)
        self.assertIn('Não houve entrega, registro permanente de pedido', texto)
        self.assertNotIn('consulta ao catálogo ainda não está disponível', texto)

    def test_terminal_esclarecimentos(self):
        texto = self.executar(['Preciso de material sobre criação', '19 anos', '6 anos', 'jogo'])
        self.assertIn('Preciso de uma informação mais específica', texto)
        self.assertIn('FIC-001', texto)

    def test_cancelamento_nao_pesquisa(self):
        for entradas in (['/sair'], ['', '/sair'], [EOFError()], [KeyboardInterrupt()]):
            with patch.object(fluxo, 'consultar') as consulta:
                self.executar(entradas)
                consulta.assert_not_called()

    def test_status_exatamente_publicado(self):
        for status in ('Rascunho', 'publicado', ' Publicado', 'Publicado ', ''):
            with self.subTest(status=status):
                dados = fluxo.materiais_ficticios()[:1]
                dados[0]['Status'] = status
                with patch.object(fluxo, 'materiais_ficticios', return_value=dados):
                    resultado = fluxo.consultar(self.pedido())
                self.assertEqual(resultado['total_encontrado'], 0)
                self.assertEqual(resultado['materiais'], [])
                self.assertEqual(resultado['pendencias'], [])

    def test_secundarios_ausentes_apresentados_com_pendencias(self):
        dados = fluxo.materiais_ficticios()[:1]
        secundarios = ('Referência bíblica', 'Palavras-chave',
                       'Origem (Drive ou OneDrive)', 'Responsável pela aprovação',
                       'Data de publicação')
        for campo in secundarios:
            dados[0][campo] = '  '
        with patch.object(fluxo, 'materiais_ficticios', return_value=dados):
            resultado = fluxo.consultar(self.pedido())
        self.assertEqual(resultado['total_encontrado'], 1)
        self.assertEqual(len(resultado['materiais']), 1)
        self.assertEqual(resultado['pendencias'][0]['campos_pendentes'], list(secundarios))
        texto = fluxo.apresentar_resultado(self.pedido(), resultado)
        self.assertIn('Publicado com campos essenciais preenchidos e cadastro incompleto: FIC-001', texto)
        self.assertIn('https://example.invalid/fic-001', texto)
        self.assertNotIn('Publicado com cadastro completo:', texto)
        for campo in secundarios:
            self.assertIn(campo, texto)
        self.assertIn('Links não foram acessados nem verificados.', texto)

    def test_encontrado_completo_e_acesso_sao_distintos(self):
        resultado = fluxo.consultar(self.pedido())
        completo, incompleto = resultado['avaliados']
        self.assertEqual(resultado['total_encontrado'], 2)
        self.assertTrue(completo['cadastro_completo'])
        self.assertTrue(completo['disponivel_para_entrega_no_catalogo'])
        self.assertFalse(incompleto['cadastro_completo'])
        self.assertFalse(incompleto['disponivel_para_entrega_no_catalogo'])
        for item in resultado['avaliados'] + resultado['materiais']:
            self.assertFalse(item['acesso_ao_arquivo_verificado'])

    def test_encontrado_sem_essenciais_nao_e_ausencia_de_correspondencia(self):
        dados = fluxo.materiais_ficticios()[1:2]
        with patch.object(fluxo, 'materiais_ficticios', return_value=dados):
            resultado = fluxo.consultar(self.pedido())
        self.assertEqual(resultado['total_encontrado'], 1)
        self.assertEqual(resultado['materiais'], [])
        texto = fluxo.apresentar_resultado(self.pedido(), resultado)
        self.assertIn('Necessidade de correção administrativa', texto)
        self.assertNotIn('Não foi encontrado', texto)

    def test_campos_de_filtro_ausentes_nao_correspondem(self):
        for campo in ('Tema bíblico', 'Faixa etária', 'Tipo de material'):
            with self.subTest(campo=campo):
                dados = fluxo.materiais_ficticios()[:1]
                dados[0][campo] = ' '
                with patch.object(fluxo, 'materiais_ficticios', return_value=dados):
                    resultado = fluxo.consultar(self.pedido())
                self.assertEqual(resultado['total_encontrado'], 0)

    def test_usa_mecanismo_oficial(self):
        original = catalogo.pesquisar
        with patch.object(catalogo, 'pesquisar', wraps=original) as pesquisa:
            fluxo.consultar(self.pedido())
        self.assertEqual(pesquisa.call_args_list[0].kwargs,
                         {'tema': 'criação', 'faixa_etaria': '6 anos', 'tipo': 'jogo'})


if __name__ == '__main__':
    unittest.main()
