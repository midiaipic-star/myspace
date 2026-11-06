"""Etapa 90: atendimento e pesquisa exclusivamente local em dados fictícios."""
import re
import catalogo
from lia import Pedido, PERGUNTAS, normalizar

AVISO = ('Simulação com dados exclusivamente fictícios. Links não foram acessados '
         'nem verificados. Não houve entrega, registro permanente de pedido ou '
         'encaminhamento ao Pesquisador.')
PLURAIS = dict(zip(
    ('atividades', 'aulas', 'jogos', 'devocionais', 'cartazes', 'historias',
     'desenhos', 'dinamicas', 'roteiros'),
    ('atividade', 'aula', 'jogo', 'devocional', 'cartaz', 'historia',
     'desenho', 'dinamica', 'roteiro')))


def materiais_ficticios():
    """Nova lista a cada chamada; nenhum arquivo ou serviço é consultado."""
    base = dict(zip(catalogo.COLUNAS, (
        'FIC-001', 'Jogo fictício da criação', 'criação', 'Gênesis 1:1',
        '4 a 8 anos', 'jogo', 'criação natureza', 'Publicado',
        'Origem fictícia', 'https://example.invalid/fic-001',
        'Equipe fictícia', '2026-11-06')))
    incompleto = dict(base, **{'Código': 'FIC-002',
        'Título do material': 'Jogo fictício com pendência', 'Link do arquivo': ' '})
    rascunho = dict(base, **{'Código': 'FIC-003', 'Status': 'Rascunho'})
    return [base, incompleto, rascunho]


def consultar(pedido):
    """Integra os módulos sem persistência e sem aceitar fontes externas."""
    if pedido.pendentes():
        raise ValueError('Esclareça tema, faixa etária e tipo antes da pesquisa.')
    # Lia também aceita dos/das; o catálogo recebe a forma canônica de idade.
    faixa = re.sub(r'^(?:de|dos|das)\s+', '',
                   normalizar(pedido.faixa_etaria).strip())
    tipo = normalizar(pedido.tipo).strip()
    encontrados = catalogo.pesquisar(
        materiais_ficticios(), tema=pedido.tema, faixa_etaria=faixa,
        tipo=PLURAIS.get(tipo, tipo))
    pendencias, avaliados, apresentaveis = [], [], []
    for avaliacao in catalogo.avaliar_entrega(encontrados):
        material = avaliacao['material']
        faltantes = [c for c in catalogo.COLUNAS if not material[c].strip()]
        avaliacao['cadastro_completo'] = not faltantes
        avaliacao['campos_pendentes'] = faltantes
        avaliados.append(avaliacao)
        if faltantes:
            pendencias.append({'material': material, 'campos_pendentes': faltantes})
        # A regra de apresentação é a mesma do catálogo: Publicado e essenciais.
        if avaliacao['disponivel_para_entrega_no_catalogo']:
            item = catalogo.apresentar([material])[0]
            item['cadastro_completo'] = not faltantes
            item['acesso_ao_arquivo_verificado'] = False
            apresentaveis.append(item)
    return {'materiais': apresentaveis, 'avaliados': avaliados,
            'pendencias': pendencias, 'total_encontrado': len(encontrados)}


def apresentar_resultado(pedido, resultado):
    linhas = [f'Tema: {pedido.tema}', f'Faixa etária: {pedido.faixa_etaria}',
              f'Tipo de material: {pedido.tipo}']
    if not resultado['total_encontrado']:
        linhas.append('Não foi encontrado material publicado correspondente entre os registros consultados.')
    for item in resultado['materiais']:
        situacao = ('Publicado com cadastro completo' if item['cadastro_completo']
                    else 'Publicado com campos essenciais preenchidos e cadastro incompleto')
        linhas.append(f"{situacao}: {item['codigo']} | "
                      f"{item['titulo']} | {item['link']}")
    for item in resultado['pendencias']:
        material = item['material']
        linhas.append('Necessidade de correção administrativa: publicado ' +
                      (material['Código'].strip() or '(sem código)') +
                      '; campos pendentes: ' + ', '.join(item['campos_pendentes']) + '.')
    linhas.append(AVISO)
    return '\n'.join(linhas)


def main():
    print('Lia — atendimento e pesquisa fictícia / Etapa 90')
    print(AVISO)
    print('Digite /sair para encerrar. Os dados ficam somente nesta sessão.')
    try:
        texto = input('Seu pedido: ').strip()
        if texto == '/sair':
            return
        pedido = Pedido.receber(texto)
        for campo in pedido.pendentes():
            while True:
                resposta = input(PERGUNTAS[campo] + '\n> ')
                if resposta.strip() == '/sair':
                    print('Atendimento encerrado. ' + AVISO)
                    return
                if pedido.esclarecer(campo, resposta):
                    break
                print('Preciso de uma informação mais específica para continuar.')
        print(apresentar_resultado(pedido, consultar(pedido)))
    except (EOFError, KeyboardInterrupt):
        print('\nAtendimento interrompido. ' + AVISO)


if __name__ == '__main__':
    main()
