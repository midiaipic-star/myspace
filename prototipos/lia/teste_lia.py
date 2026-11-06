import subprocess
import sys
import unittest
from pathlib import Path
from lia import AVISO, Pedido


class TestLia(unittest.TestCase):
    def test_completo(self):
        p = Pedido.receber('Quero uma atividade sobre a criação para crianças de 4 a 6 anos.')
        self.assertEqual((p.tema, p.faixa_etaria, p.tipo), ('a criação', 'de 4 a 6 anos', 'atividade'))
        self.assertEqual(p.pendentes(), [])

    def test_campos_explicitos(self):
        p = Pedido.receber('Tema: Bom Samaritano; faixa etária: 7 a 9 anos; tipo: teatro; observações: 20 crianças')
        self.assertEqual(p.pendentes(), [])
        self.assertIn('20 crianças', p.resumo())

    def test_incompleto(self):
        p = Pedido.receber('Quero material sobre oração')
        self.assertEqual(p.pendentes(), ['faixa_etaria', 'tipo'])
        self.assertTrue(p.esclarecer('faixa_etaria', '6 anos'))
        self.assertTrue(p.esclarecer('tipo', 'jogo'))
        self.assertEqual(p.tema, 'oração')
        self.assertFalse(p.pendentes())

    def test_vazio(self):
        p = Pedido.receber('')
        self.assertEqual(len(p.pendentes()), 3)
        self.assertFalse(p.esclarecer('tema', '  '))
        self.assertFalse(p.esclarecer('tema', 'não sei'))

    def test_ambiguo(self):
        p = Pedido.receber('Quero aula ou jogo sobre oração ou fé para crianças')
        self.assertEqual(len(p.pendentes()), 3)

    def test_idades_invalidas(self):
        for idade in ('9 a 4 anos', '99 anos', 'crianças', '4 ou 8 anos'):
            p = Pedido.receber('')
            self.assertFalse(p.esclarecer('faixa_etaria', idade))

    def test_honestidade(self):
        p = Pedido.receber('Tema: Natal; faixa etária: 5 anos; tipo: aula')
        self.assertIn(AVISO, p.resumo())
        self.assertIn('ainda não foi verificada', p.resumo())
        self.assertIn('apenas nesta sessão', p.resumo())

    def executar(self, entrada):
        return subprocess.run([sys.executable, str(Path(__file__).with_name('lia.py'))],
                              input=entrada, text=True, capture_output=True, check=True).stdout

    def test_terminal_esclarecimentos(self):
        saida = self.executar('Preciso de material\noração\npequenos\n4 a 6 anos\njogo\n')
        self.assertIn('Qual é o tema', saida)
        self.assertIn('mais específica', saida)
        self.assertIn('Tema: oração', saida)
        self.assertIn('Faixa etária: 4 a 6 anos', saida)
        self.assertIn('Tipo de material: jogo', saida)
        self.assertIn(AVISO, saida)

    def test_terminal_completo(self):
        saida = self.executar('Quero uma aula sobre Natal para crianças de 6 anos\n')
        self.assertNotIn('Qual é', saida)
        self.assertIn('Tema: Natal', saida)

    def test_interrupcao(self):
        saida = self.executar('Preciso de material\n/sair\n')
        self.assertIn('aguardando esclarecimentos', saida)
        self.assertIn(AVISO, saida)


if __name__ == '__main__':
    unittest.main()
