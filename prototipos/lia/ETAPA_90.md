# Etapa 90 — integração local e fictícia

Novos arquivos: `integracao.py`, `test_integracao.py` e este documento.
Os arquivos oficiais existentes foram preservados.

## Executar na raiz do repositório

```sh
python3 prototipos/lia/integracao.py
```

Pedido de exemplo:

```text
tema: criação; faixa etária: 6 anos; tipo: jogo
```

Também aceita: `Quero jogos sobre criação para crianças de 6 anos.`
Pedidos incompletos recebem perguntas da Lia. `/sair`, EOF e Ctrl+C encerram.

O programa usa `Pedido` e `PERGUNTAS` de lia.py, e `pesquisar`,
`avaliar_entrega` e `apresentar` de catalogo.py. Não usa o resumo antigo da Lia,
cujo aviso pertence à etapa anterior sem integração.

A fonte é exclusivamente a lista fictícia criada em memória, sem parâmetro de
fonte externa. Os links usam example.invalid. Não há rede, arquivos de pedidos,
encaminhamento, acesso a links ou entrega. Nenhum serviço de armazenamento é
consultado. A origem e os responsáveis também são fictícios.

A pesquisa combina tema, cobertura integral da idade e tipo, exigindo Publicado.
A integração converte plurais conhecidos para singular e os prefixos de idade
aceitos pela Lia para o formato do catálogo. Não infere sinônimos, equivalências
bíblicas ou temas. Valem os limites de interpretação determinística da Lia.

A apresentação segue a regra oficial do catálogo: status exatamente `Publicado`
e código, título e link preenchidos (somente espaços contam como ausência).
Essa disponibilidade é apenas cadastral; não comprova acesso ou entrega.

Cadastro completo significa as 12 colunas oficiais preenchidas. Campos
secundários ausentes geram pendências administrativas, mas não bloqueiam a
apresentação quando os essenciais estão preenchidos. Nesse caso, a saída indica
“Publicado com campos essenciais preenchidos e cadastro incompleto” e lista as
pendências. Sem os essenciais, o registro encontrado aparece somente como
pendência administrativa, sem apresentação de material.

O resultado distingue `total_encontrado`, `materiais` apresentados, `pendencias`
e `avaliados`. Cada avaliação informa `cadastro_completo`,
`disponivel_para_entrega_no_catalogo` e `acesso_ao_arquivo_verificado` (sempre
False). Os materiais apresentados também informam cadastro completo e acesso
não verificado. Presença textual não valida links, datas ou aprovação.

Campos usados como filtro que estejam ausentes não correspondem à pesquisa;
não há auditoria global do catálogo neste fluxo. Se não houver publicado
correspondente, a resposta é exatamente:

> Não foi encontrado material publicado correspondente entre os registros consultados.

Um publicado correspondente sem os essenciais continua contado como encontrado;
nessa situação são informadas as pendências, sem mensagem de ausência.

## Verificação

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s prototipos/lia -v
```

Resultado em 06/11/2026: 53 testes aprovados, sendo 16 da integração e 37
existentes. Cobertura nova: completos/incompletos, campos ausentes, filtros
combinados, faixa integral, ausência de correspondência, adaptações de entrada,
pedido incompleto, preservação dos dados, terminal, esclarecimentos,
cancelamento/interrupção e chamada ao mecanismo oficial. Os 11 cenários anteriores
foram mantidos, com atualização das expectativas afetadas pela nova regra.
Cinco testes adicionais verificam status exato, múltiplos secundários ausentes,
distinção entre encontrado/cadastro/acesso, encontrado sem essenciais e ausência
de campos usados nos filtros. Os testes oficiais existentes não foram alterados.

## Fontes oficiais consultadas

Consulta pelo conector GitHub à branch main:
https://github.com/midiaipic-star/myspace/tree/main/prototipos/lia

Blobs consultados e conferidos contra os módulos locais:

- lia.py: c99cbdff6ce840907250c7b12c05d25bba19d680
- catalogo.py: a0f3adff1a2740514735bef9f36e4705e6569022

Sem commits, push ou alterações remotas.
