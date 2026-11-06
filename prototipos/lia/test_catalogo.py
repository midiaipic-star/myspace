"""Dados fictícios exclusivos de teste; domínio .invalid sem material real."""
import copy
import unittest
from unittest.mock import patch
from catalogo import COLUNAS, pesquisar, apresentar, avaliar_entrega

def material(**mudancas):
    m = dict.fromkeys(COLUNAS, '')
    m.update({'Código': 'TESTE-001', 'Título do material': 'Atividade fictícia',
              'Tema bíblico': 'A criação', 'Referência bíblica': 'Gênesis 1:1-5',
              'Faixa etária': '4 a 8 anos', 'Tipo de material': 'Atividade',
              'Palavras-chave': 'criação; natureza; gratidão', 'Status': 'Publicado',
              'Origem (Drive ou OneDrive)': 'Drive',
              'Link do arquivo': 'https://exemplo.invalid/ficticio',
              'Responsável pela aprovação': 'Pessoa fictícia',
              'Data de publicação': '2026-01-01'})
    m.update(mudancas)
    return m

class TestCatalogo(unittest.TestCase):
    def setUp(self):
        self.itens = [material(), material(**{
            'Código': 'TESTE-002', 'Tema bíblico': 'Oração',
            'Referência bíblica': 'Mateus 6:9-13', 'Tipo de material': 'Jogo',
            'Palavras-chave': 'oração; confiança', 'Faixa etária': '9 a 12 anos'})]

    def test_combinacao(self):
        r = pesquisar(self.itens, tema='CRIACAO', referencia='GENESIS 1 : 1 - 5',
                      faixa_etaria='6 anos', tipo='ATIVIDADE',
                      palavras_chave=['NATUREZA', 'GRATIDAO'])
        self.assertEqual([m['Código'] for m in r], ['TESTE-001'])

    def test_sem_resultado(self):
        self.assertEqual(pesquisar(self.itens, tema='Dilúvio'), [])

    def test_lista_vazia(self):
        self.assertEqual(pesquisar([], tema='Criação'), [])

    def test_status_exato(self):
        for s in ('Aprovado', 'Em revisão', 'Em produção', '', 'publicado', 'PUBLICADO', 'Publicado '):
            with self.subTest(status=s):
                self.assertEqual(pesquisar([material(Status=s)], tema='criação'), [])

    def test_status_mistos(self):
        self.assertEqual(len(pesquisar([material(Status=s) for s in
                                       ('Aprovado', 'Publicado', '', 'Em revisão')])), 1)

    def test_referencias_diferentes(self):
        for ref in ('Gênesis 1:10-15', 'Gênesis 1:1', 'Gn 1:1-5'):
            with self.subTest(ref=ref):
                self.assertEqual(pesquisar(self.itens, referencia=ref), [])

    def test_tipo(self):
        self.assertEqual(pesquisar(self.itens, tema='criação', tipo='Jogo'), [])
        self.assertEqual(len(pesquisar(self.itens, tipo='jOgO')), 1)

    def test_palavras_chave(self):
        self.assertEqual(pesquisar(self.itens, palavras_chave=['natureza', 'oração']), [])
        self.assertEqual(len(pesquisar(self.itens, palavras_chave='CONFIANÇA')), 1)

    def test_fragmentos_nao_correspondem(self):
        self.assertEqual(pesquisar(self.itens, tema='ação'), [])
        self.assertEqual(pesquisar(self.itens, palavras_chave='gra'), [])

    def test_intervalo_completo(self):
        self.assertEqual(len(pesquisar(self.itens, faixa_etaria='4 até 8 anos')), 1)
        self.assertEqual(pesquisar(self.itens, faixa_etaria='7 a 10 anos'), [])
        self.assertEqual(pesquisar(self.itens, faixa_etaria='0 anos'), [])

    def test_limites_idade(self):
        self.assertEqual(len(pesquisar([material(**{'Faixa etária': '0-17 anos'})],
                                       faixa_etaria='0 a 17 anos')), 1)

    def test_idade_solicitada_invalida(self):
        for faixa in ('8 a 4 anos', '18 anos', 'bebês', '4 ou 8 anos'):
            with self.subTest(faixa=faixa), self.assertRaises(ValueError):
                pesquisar(self.itens, faixa_etaria=faixa)

    def test_idade_cadastrada_desconhecida(self):
        self.assertEqual(pesquisar([material(**{'Faixa etária': 'pequenos'})],
                                   faixa_etaria='6 anos'), [])

    def test_apresentacao(self):
        self.assertEqual(apresentar(pesquisar(self.itens, tema='criação')), [{
            'codigo': 'TESTE-001', 'titulo': 'Atividade fictícia',
            'link': 'https://exemplo.invalid/ficticio'}])

    def test_dados_ausentes_nao_inventados(self):
        incompleto = material(**{'Link do arquivo': ''})
        self.assertEqual(apresentar([incompleto]), [])
        self.assertEqual(pesquisar([incompleto])[0]['Link do arquivo'], '')
        self.assertEqual(apresentar([]), [])

    def test_apresentacao_nao_publicado(self):
        with self.assertRaises(ValueError):
            apresentar([material(Status='Aprovado')])

    def test_estrutura(self):
        for m in ({}, {**material(), 'Extra': ''}):
            with self.subTest(m=m), self.assertRaises(ValueError):
                pesquisar([m])
        with self.assertRaises(TypeError):
            pesquisar([material(**{'Código': 123})])

    def test_filtros_invalidos(self):
        with self.assertRaises(TypeError):
            pesquisar(self.itens, tema=None)
        for palavras in ([''], [None], ['!!!']):
            with self.subTest(palavras=palavras), self.assertRaises(ValueError):
                pesquisar(self.itens, palavras_chave=palavras)

    def test_preserva_entrada(self):
        antes = copy.deepcopy(self.itens)
        r = pesquisar(self.itens)
        r[0]['Título do material'] = 'Alterado só na cópia'
        self.assertEqual(self.itens, antes)

    def test_sem_filtros(self):
        self.assertEqual(pesquisar(self.itens, tema='  '), self.itens)

    def test_ausencia_de_cada_campo_impede_apresentacao(self):
        for campo in ('Código', 'Título do material', 'Link do arquivo'):
            for vazio in ('', '  ', '\t\n'):
                with self.subTest(campo=campo, vazio=vazio):
                    item = material(**{campo: vazio})
                    self.assertEqual(pesquisar([item], tema='criação'), [item])
                    self.assertEqual(apresentar([item]), [])
                    avaliacao = avaliar_entrega([item])[0]
                    self.assertEqual(avaliacao['material'], item)
                    self.assertEqual(avaliacao['campos_pendentes'], [campo])
                    self.assertFalse(avaliacao['disponivel_para_entrega_no_catalogo'])

    def test_todos_os_campos_pendentes_identificados(self):
        item = material(**{'Código': '', 'Título do material': ' ', 'Link do arquivo': ''})
        self.assertEqual(avaliar_entrega([item])[0]['campos_pendentes'],
                         ['Código', 'Título do material', 'Link do arquivo'])

    def test_completos_e_incompletos_separados(self):
        itens = [material(**{'Código': ''}), material(),
                 material(**{'Link do arquivo': ' '})]
        avaliados = avaliar_entrega(pesquisar(itens, tema='criação'))
        self.assertEqual([a['disponivel_para_entrega_no_catalogo'] for a in avaliados],
                         [False, True, False])
        self.assertEqual(apresentar(itens), apresentar([itens[1]]))
        self.assertEqual(len(pesquisar(itens)), 3)

    def test_avaliacao_e_apresentacao_exigem_status_exato(self):
        for status in ('Aprovado', 'Em revisão', 'Em produção', '',
                       'publicado', 'PUBLICADO', 'Publicado '):
            with self.subTest(status=status):
                item = material(Status=status)
                self.assertEqual(avaliar_entrega([item]), [])
                with self.assertRaises(ValueError):
                    apresentar([item])

    def test_disponibilidade_cadastral_nao_comprova_acesso(self):
        with patch('urllib.request.urlopen') as abrir, patch('socket.create_connection') as conectar:
            encontrados = pesquisar([material()], tema='criação')
            avaliacao = avaliar_entrega(encontrados)[0]
            self.assertTrue(avaliacao['disponivel_para_entrega_no_catalogo'])
            self.assertFalse(avaliacao['acesso_ao_arquivo_verificado'])
            self.assertEqual(avaliacao['campos_pendentes'], [])
            self.assertEqual(apresentar(encontrados)[0]['link'],
                             'https://exemplo.invalid/ficticio')
            abrir.assert_not_called()
            conectar.assert_not_called()

    def test_avaliacao_preserva_dados_e_copias(self):
        itens = [material(**{'Código': ' TESTE-001 ', 'Link do arquivo': ' '})]
        antes = copy.deepcopy(itens)
        avaliados = avaliar_entrega(itens)
        self.assertEqual(avaliados[0]['material'], antes[0])
        avaliados[0]['material']['Código'] = 'Alteração na cópia'
        self.assertEqual(itens, antes)
        self.assertEqual(apresentar(itens), [])
        self.assertEqual(itens, antes)

    def test_avaliacao_vazia(self):
        self.assertEqual(avaliar_entrega([]), [])

if __name__ == '__main__':
    unittest.main()
