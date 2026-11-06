# Protótipo local da Lia

Atendimento de terminal em português, com Python 3.10 ou superior e somente
biblioteca padrão. Não requer instalação, internet, chaves ou serviços externos.

## Executar

Na raiz do repositório:

```sh
python3 prototipos/lia/lia.py
```

Exemplo de pedido completo:

```text
Quero uma atividade sobre a criação para crianças de 4 a 6 anos.
```

Exemplo incompleto: `Preciso de material sobre oração`. Lia pergunta a idade e
o tipo de material. Responda, por exemplo, `6 anos` e `jogo`.
Respostas de esclarecimento devem conter apenas o valor solicitado.
Use `/sair` para interromper. EOF e Ctrl+C também encerram o atendimento.

Para temas ou formatos livres, use campos separados por ponto e vírgula:

```text
Tema: Bom Samaritano; faixa etária: 7 a 9 anos; tipo: teatro; observações: 20 crianças
```

O resumo inclui o texto original e os esclarecimentos para preservar observações.
O resumo final permite conferir a interpretação feita pelas regras.

## Limites desta etapa

- Extração determinística por padrões, sem modelo de linguagem. Texto livre
  reconhece tema após `sobre` ou `tema`, idades numéricas em anos e alguns tipos
  comuns. Outras construções exigem esclarecimentos.
- Idades aceitas: de 0 a 17 anos, em idade única ou intervalo crescente.
  Nomes de turmas e idades em meses precisam ser esclarecidos em anos.
- Alternativas reconhecidas no pedido inicial são tratadas como dúvida.
  Não há compreensão geral de negação, correções ou ambiguidades semânticas;
  os campos explícitos e as respostas diretas são a interface mais previsível.
- Dados somente em memória durante o processo. Não há protocolo, armazenamento
  permanente, consulta, catálogo simulado, entrega, encaminhamento ou prazos.
- A disponibilidade nunca é inferida: o resumo informa que ainda não foi verificada.

## Testes

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s prototipos/lia -v
```

Dez testes cobrem pedido completo, campos explícitos com observações, pedido
incompleto e esclarecimentos, entrada vazia, alternativas ambíguas, idades
inválidas, comunicação honesta e três fluxos reais do terminal (completo,
esclarecimentos com repetição e interrupção). Resultado verificado: 10 aprovados
em Python 3.12.14.

## Referência e arquivos para o GitHub

Especificação consultada diretamente na branch `main`, em 06/11/2026:
https://github.com/midiaipic-star/myspace/blob/main/agencia-ministerio-infantil/agentes/secretaria.md

SHA do blob consultado: `cb43684e1cc4ad1d9043b305387952d1aca44861`.
O documento oficial não foi modificado nem recriado.

Arquivos do protótipo:

- `prototipos/lia/lia.py`
- `prototipos/lia/test_lia.py`
- `prototipos/lia/README.md`
