# Etapa 108 — leitor autenticado independente

Arquivos novos: leitor_sheets.py, test_leitor_sheets.py, requirements_sheets.txt
e este documento. Os oito arquivos da main foram consultados diretamente no
GitHub e comparados por hash Git com o workspace antes do desenvolvimento.
Todos foram preservados. Não foram criadas credenciais nem ativado faturamento.

## Contrato

`ler_catalogo(aba, timeout=20)` lê o ID oficial fixado em PLANILHA_ID usando
Sheets API v4, GET de values, intervalo `'nome da aba'!A1:L`, dimensão ROWS e
FORMATTED_VALUE. O nome da aba deve ser informado explicitamente; não é inferido.
Cabeçalhos na primeira linha devem ser exatamente COLUNAS de catalogo.py, na
mesma ordem. O leitor não verifica colunas além de L nem acessa links de arquivos.

Retorna uma lista de dicionários com os 12 campos textuais. Completa células
finais omitidas e None com texto vazio; preserva textos, status, ordem e registros
incompletos. Ignora linhas inteiramente vazias ou só com espaços. Não filtra por
Publicado: a pesquisa e a apresentação continuam sob responsabilidade do catálogo.
Não executa fórmulas localmente; lê o valor formatado devolvido pela API.

Somente uma resposta válida com cabeçalho e sem registros preenchidos retorna
[]. Cabeçalho ausente, inválido, JSON inválido, erro HTTP ou falha de conexão
levantam ErroLeituraSheets ou suas subclasses ErroAutenticacaoSheets e
ErroEstruturaSheets. O chamador deve informar consulta não concluída; nunca
converter essas exceções para [] ou para uma mensagem de ausência de materiais.
Não há fallback fictício, gravação de pedidos, escrita em planilha ou entrega.

## Autenticação e dependências

Importações do SDK são tardias; os 53 testes existentes e os novos testes isolados
não precisam instalar dependências nem configurar ADC. Para uso real, em ambiente
Python 3.10+ apropriado, instalar requirements_sheets.txt (google-auth e requests).

O módulo chama google.auth.default(scopes=ESCOPOS), solicitando somente:
https://www.googleapis.com/auth/spreadsheets.readonly

Usa uma sessão HTTP com timeout para requisição e renovação. A versão atual
aceita somente google.auth.compute_engine.Credentials, para identidade vinculada
ao runtime Google Cloud. ADC local de usuário, chaves privadas, federação direta
e impersonação não são aceitas nesta versão. Não há fallback de autenticação.

A identidade esperada é exclusivamente:
lia-kingdom-kids@kingdom-kids-lab.iam.gserviceaccount.com

Antes de cada GET ao catálogo, chama refresh() das credenciais vinculadas via
google-auth e só então confere valid, token e service_account_email. O email
resolvido deve ser exatamente a conta exclusiva da Lia; alias default não resolvido,
identidade incorreta ou falha de atualização bloqueiam a leitura. A origem da
identidade é o metadata server confiável do runtime Google Cloud, não tokeninfo.
A infraestrutura deve manter a integridade do runtime e da configuração ADC.

O campo email de tokeninfo não é utilizado: pode estar ausente sem userinfo.email.
Nenhum escopo de email, identidade ou cloud-platform foi acrescentado.

### Avaliação de tokeninfo em produção

Tokeninfo não é necessário para a autenticação normal da Sheets API. Nesta versão,
foi mantido exclusivamente para verificar validade positiva e o conjunto exato de
escopos efetivamente emitidos. Apenas google.auth.default(scopes=...) ou a
propriedade scopes não comprovam isso: no Compute Engine, o metadata server pode
ignorar os escopos solicitados. Remover essa inspeção sem outro mecanismo confiável
de comprovação enfraqueceria a política de rejeitar tokens amplos.

A inspeção agora usa POST para https://www.googleapis.com/oauth2/v1/tokeninfo,
com access_token no corpo application/x-www-form-urlencoded, conforme exemplo
oficial do Google Cloud SDK. Nenhum token é colocado em URL ou query string pelo
módulo. Há uma inspeção por leitura: indisponibilidade, limitação de taxa ou resposta
inconclusiva resultam em ErroAutenticacaoSheets, sem consultar a planilha. Esse custo
e dependência de rede devem ser avaliados antes de implantar em produção; não há
fallback permissivo. O mesmo token inspecionado é enviado no cabeçalho Authorization
à Sheets API, sem renovação automática entre inspeção e leitura.

O módulo não cria logs de tokens, cabeçalhos ou corpos de autenticação e suprime
mensagens sensíveis de exceções do provedor. POST reduz exposição em URLs, mas não
impede captura de corpos/cabeçalhos por instrumentação externa: não habilitar logs
HTTP detalhados que coletem esses dados. Redirecionamentos estão desabilitados.

A inspeção do token confirma validade e escopos OAuth, não enumera todos os papéis
IAM ou compartilhamentos da identidade. A autorização ao catálogo é avaliada pela
Sheets API: HTTP 401/403 vira falha clara de autenticação/autorização, nunca [] ou
ausência de material. A configuração deve manter a conta como Leitor da planilha;
o módulo não afirma que verificou todas as permissões administrativas efetivas. Rejeita credenciais
ADC do tipo google.oauth2.service_account.Credentials, que dependem de chave
privada. Não recebe caminho de chave, não cria credenciais e não inicia login.
Providencie ADC sem chave por identidade vinculada da conta exclusiva da Lia.
O runtime precisa emitir o token com apenas o escopo solicitado. Caso emita token
cloud-platform ou outros escopos extras, a leitura falha deliberadamente: não há
redução silenciosa de permissões. Compartilhe somente o catálogo como Leitor com
essa conta, mantendo a planilha Restrita. O módulo não configura IAM, runtime ou
compartilhamentos e não cria credenciais.

## Exemplo de uso futuro (não executado contra a planilha)

```python
from leitor_sheets import ler_catalogo, ErroLeituraSheets
