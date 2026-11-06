"""Pesquisa local, sem rede. Filtros combinados por E; [] indica ausência nos
dados recebidos, não no Google Sheets. Referências comparam texto completo,
sem inferir abreviações ou equivalências bíblicas. Idades exigem cobertura total.
"""
import re
import unicodedata

COLUNAS = (
    'Código', 'Título do material', 'Tema bíblico', 'Referência bíblica',
    'Faixa etária', 'Tipo de material', 'Palavras-chave', 'Status',
    'Origem (Drive ou OneDrive)', 'Link do arquivo',
    'Responsável pela aprovação', 'Data de publicação',
)

def _normalizar(texto):
    return ' '.join(''.join(
        c for c in unicodedata.normalize('NFD', texto.casefold())
        if unicodedata.category(c) != 'Mn'
    ).split())

def _contem(texto, termo):
    fonte = re.findall(r'\w+', _normalizar(texto))
    alvo = re.findall(r'\w+', _normalizar(termo))
    return bool(alvo) and any(
        fonte[i:i + len(alvo)] == alvo for i in range(len(fonte) - len(alvo) + 1)
    )

def _referencia(texto):
    return re.sub(r'\s*([:-])\s*', r'\1', _normalizar(texto))

def _idade(texto):
    m = re.fullmatch(
        r'(?:de\s+)?(\d{1,2})\s*(?:(?:a|ate|-)\s*(\d{1,2})\s*)?anos?',
        _normalizar(texto))
    if m:
        inicio, fim = int(m[1]), int(m[2] or m[1])
        if 0 <= inicio <= fim <= 17:
            return inicio, fim
    raise ValueError('Use uma idade ou intervalo crescente entre 0 e 17 anos.')

def pesquisar(materiais, *, tema='', referencia='', faixa_etaria='', tipo='', palavras_chave=()):
    """Recebe lista de dicionários com exatamente as 12 colunas, valores textuais.
    Tema e palavras-chave buscam palavras inteiras consecutivas, sem acentos/caixa.
    Todas as palavras-chave solicitadas devem corresponder no campo Palavras-chave.
    Tipo compara texto completo; status exige exatamente Publicado.
    Sem filtros retorna todos os publicados, inclusive registros incompletos.
    Encontrado não significa disponível para entrega. Retorna cópias na ordem recebida.
    Erros de estrutura/filtro geram exceção. Faixa cadastrada inválida não
    corresponde a uma busca por idade. Não acessa nem verifica links.
    """
    if not isinstance(materiais, list):
        raise TypeError('materiais deve ser lista.')
    if any(not isinstance(v, str) for v in (tema, referencia, faixa_etaria, tipo)):
        raise TypeError('Filtros devem ser textos.')
    if isinstance(palavras_chave, str):
        palavras_chave = (palavras_chave,)
    if not isinstance(palavras_chave, (list, tuple)):
        raise TypeError('palavras_chave deve ser texto, lista ou tupla.')
    if any(not isinstance(p, str) or not _contem(p, p) for p in palavras_chave):
        raise ValueError('Palavras-chave devem conter texto pesquisável.')
    if tema.strip() and not _contem(tema, tema):
        raise ValueError('Tema deve conter texto pesquisável.')
    faixa = _idade(faixa_etaria) if faixa_etaria.strip() else None
    encontrados = []
    for indice, material in enumerate(materiais):
        if not isinstance(material, dict) or set(material) != set(COLUNAS):
            raise ValueError(f'Registro {indice}: esperadas as 12 colunas oficiais.')
        if any(not isinstance(v, str) for v in material.values()):
            raise TypeError('Valores devem ser textos; use vazio para ausentes.')
        if material['Status'] != 'Publicado':
            continue
        if tema.strip() and not _contem(material['Tema bíblico'], tema):
            continue
        if referencia.strip() and _referencia(material['Referência bíblica']) != _referencia(referencia):
            continue
        if tipo.strip() and _normalizar(material['Tipo de material']) != _normalizar(tipo):
            continue
        if not all(_contem(material['Palavras-chave'], p) for p in palavras_chave):
            continue
        if faixa:
            try:
                inicio, fim = _idade(material['Faixa etária'])
            except ValueError:
                continue
            if not inicio <= faixa[0] <= faixa[1] <= fim:
                continue
        encontrados.append(dict(material))
    return encontrados

def avaliar_entrega(materiais):
    """Classifica os publicados sem descartar registros incompletos.

    Disponibilidade aqui significa apenas status Publicado e presença de código,
    título e link no catálogo. Não comprova acesso ao arquivo nem entrega.
    campos_pendentes permite futura correção administrativa; valores compostos
    apenas por espaços são ausentes. Os dados originais são preservados.
    Registros de outros status são ignorados, como na pesquisa.
    """
    avaliados = []
    for material in pesquisar(materiais):
        pendentes = [campo for campo in ('Código', 'Título do material', 'Link do arquivo')
                     if not material[campo].strip()]
        avaliados.append({
            'material': material,
            'campos_pendentes': pendentes,
            'disponivel_para_entrega_no_catalogo': not pendentes,
            'acesso_ao_arquivo_verificado': False,
        })
    return avaliados


def apresentar(materiais):
    """Retorna código, título e link originais dos disponíveis no catálogo.

    Exige status exatamente Publicado; rejeita listas com outros status.
    Omite registros sem código, título ou link (inclusive somente espaços).
    Eles continuam acessíveis por pesquisar() e avaliar_entrega().
    Não acessa nem valida links, não comprova acesso e não realiza entrega.
    """
    publicados = pesquisar(materiais)
    if len(publicados) != len(materiais):
        raise ValueError('Somente publicados podem ser apresentados.')
    return [
        {'codigo': a['material']['Código'], 'titulo': a['material']['Título do material'],
         'link': a['material']['Link do arquivo']}
        for a in avaliar_entrega(publicados)
        if a['disponivel_para_entrega_no_catalogo']
    ]
