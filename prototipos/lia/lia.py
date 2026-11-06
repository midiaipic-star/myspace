"""Triagem local da Lia. Apenas biblioteca padrão; nenhum acesso externo."""
import re
import unicodedata
from dataclasses import dataclass, field


AVISO = (
    "A consulta ao catálogo ainda não está disponível. "
    "A disponibilidade do material ainda não foi verificada. "
    "Não houve registro permanente, entrega ou encaminhamento ao Pesquisador."
)


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto.lower())
                   if unicodedata.category(c) != 'Mn')


def idade_valida(texto):
    t = normalizar(texto).strip()
    m = re.fullmatch(r'(?:de |dos |das )?(\d{1,2})\s*(?:(?:a|ate|-)\s*(\d{1,2})\s*)?anos?', t)
    return bool(m and 0 <= int(m[1]) <= int(m[2] or m[1]) <= 17)


@dataclass
class Pedido:
    tema: str = ''
    faixa_etaria: str = ''
    tipo: str = ''
    mensagens: list = field(default_factory=list)

    @classmethod
    def receber(cls, texto):
        p = cls(mensagens=[texto])
        # Campos explícitos permitem qualquer tema ou tipo sem adivinhação.
        campos = {}
        for parte in texto.split(';'):
            m = re.fullmatch(r'\s*([^:]+):\s*(.*?)\s*', parte)
            if m:
                campos[normalizar(m[1]).strip()] = m[2]
        p.tema = campos.get('tema', '')
        p.tipo = campos.get('tipo', '')
        faixa = campos.get('faixa etaria', '')
        if idade_valida(faixa):
            p.faixa_etaria = faixa
        if campos:
            return p
        # Texto livre: aceita somente padrões reconhecidos; dúvidas viram perguntas.
        t = normalizar(texto)
        tipos = re.findall(r'\b(?:atividades?|aulas?|jogos?|devocionais|devocional|cartazes?|historias?|desenhos?|dinamicas?|roteiros?)\b', t)
        if len(tipos) == 1 and not re.search(r'\b(?:ou|talvez|nao)\b', t):
            p.tipo = tipos[0]
        idades = list(re.finditer(r'\b(?:de\s+)?\d{1,2}\s*(?:(?:a|ate|-)\s*\d{1,2}\s*)?anos?\b', t))
        if len(idades) == 1:
            trecho = texto[idades[0].start():idades[0].end()]
            if idade_valida(trecho):
                p.faixa_etaria = trecho
        m = re.search(r'\b(?:sobre|tema)\s+(.+?)(?=\s+para\b|[;.!?]|$)', texto, re.I)
        if m and not re.search(r'\b(?:ou|talvez|nao sei)\b', normalizar(m[1])):
            p.tema = m[1].strip()
        return p

    def pendentes(self):
        return [nome for nome in ('tema', 'faixa_etaria', 'tipo') if not getattr(self, nome)]

    def esclarecer(self, campo, resposta):
        if campo not in self.pendentes():
            raise ValueError('Campo não está pendente.')
        resposta = resposta.strip()
        if not resposta or normalizar(resposta) in ('nao sei', 'qualquer', 'tanto faz'):
            return False
        if campo == 'faixa_etaria' and not idade_valida(resposta):
            return False
        setattr(self, campo, resposta)
        self.mensagens.append(f'{campo}: {resposta}')
        return True

    def resumo(self):
        linhas = [
            'Resumo do pedido — Lia / Kingdom Kids Lab',
            f'Tema: {self.tema or "A esclarecer"}',
            f'Faixa etária: {self.faixa_etaria or "A esclarecer"}',
            f'Tipo de material: {self.tipo or "A esclarecer"}',
            'Informações originais e esclarecimentos:',
            *[f'  - {m}' for m in self.mensagens],
            'Situação: ' + ('aguardando esclarecimentos.' if self.pendentes() else 'triagem concluída apenas nesta sessão.'),
            AVISO,
            'Próxima etapa prevista: consultar o catálogo quando a integração estiver implementada.',
        ]
        return '\n'.join(linhas)


PERGUNTAS = {
    'tema': 'Qual é o tema desejado? Se houver alternativas, informe o tema escolhido.',
    'faixa_etaria': 'Qual é a faixa etária? Informe uma idade ou intervalo, como 6 anos ou 4 a 8 anos (0 a 17).',
    'tipo': 'Qual tipo de material você deseja? Especifique o formato ou os formatos escolhidos.',
}


def main():
    print('Olá! Sou a Lia, do Kingdom Kids Lab. Vamos organizar seu pedido de material?')
    print('Para encerrar a qualquer momento, digite /sair. Os dados ficam apenas nesta sessão.')
    pedido = None
    try:
        texto = input('Seu pedido: ').strip()
        if texto == '/sair':
            return
        pedido = Pedido.receber(texto)
        for campo in pedido.pendentes():
            while True:
                resposta = input(PERGUNTAS[campo] + '\n> ')
                if resposta.strip() == '/sair':
                    print(pedido.resumo())
                    return
                if pedido.esclarecer(campo, resposta):
                    break
                print('Preciso de uma informação mais específica para continuar.')
        print(pedido.resumo())
    except (EOFError, KeyboardInterrupt):
        print('\nAtendimento interrompido.')
        if pedido:
            print(pedido.resumo())


if __name__ == '__main__':
    main()
