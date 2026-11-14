# Migração do armazenamento para o Turso

O Render (plano free) tem disco efêmero: o `users.db` local some a cada
deploy/reinício. O Turso é um SQLite hospedado (libSQL) que mantém os dados
fora do servidor. O backend usa o pacote Python `libsql` (versão fixada em
`backend/requirements-docker.txt`).

> Os nomes de menus e telas do Turso abaixo **podem diferir** da interface
> atual. Os comandos da CLI (`turso ...`) citados aqui **não foram verificados**:
> confira na documentação do Turso (https://docs.turso.tech) antes de usar,
> principalmente `turso db show --url`, `turso db shell ... .dump` e
> `turso db tokens invalidate`.

## 1. Criar a conta e o banco

1. Crie uma conta em https://turso.tech e escolha o plano gratuito (free).
2. Use o painel web (dashboard) **ou** a CLI (`turso`). Pela CLI:
   ```
   turso auth login
   turso db create studex-teste --location <regiao>   # banco DESCARTÁVEL para o smoke test
   turso db create studex-prod  --location <regiao>   # banco de produção
   ```
3. **Escolha a região mais próxima da região do serviço no Render** (veja em
   Render → Settings; `turso db locations` lista as opções do Turso — confira
   o comando na documentação). Isso é o que mais pesa no desempenho: cada
   consulta é uma ida e volta de rede, e o app atende uma consulta por vez.
   Teste real (Brasil → Turso fora do país): centenas de ms por consulta. Na
   mesma região do Render, poucos ms.
4. Obtenha a URL de cada banco (confira na documentação do Turso o comando
   atual; hoje seria `turso db show studex-prod --url`) no formato `libsql://<nome>-<org>.turso.io`).

## 2. Criar o token

- Prefira um token **restrito ao banco** (não um token de toda a conta). Na CLI:
  `turso db tokens create studex-prod` (opções de expiração e somente-leitura
  podem existir; confira `turso db tokens create --help`).
- Crie tokens **separados** para o banco de teste e o de produção.
- Rotação: crie um token novo, atualize a variável no Render, faça o redeploy,
  confirme que funciona e só então revogue o antigo (`turso db tokens invalidate`
  invalida os tokens do banco; confira na documentação do Turso se o comando
  existe e se aplica ao seu caso).
- O token é um segredo: dá acesso total aos dados pessoais dos usuários.
  Nunca o coloque no Git, em logs, prints ou chats.

## 3. Testar com o script de fumaça (banco de TESTE)

Rode no seu computador, **nunca** apontando para o banco de produção:

```
pip install -r backend/requirements-docker.txt     # (ou apenas: pip install libsql==0.1.11)
export TURSO_DATABASE_URL="libsql://studex-teste-<org>.turso.io"
export TURSO_AUTH_TOKEN="<token do banco de teste>"
cd backend/src
python ../../scripts/turso_smoke.py --i-understand-this-writes-test-data
```

O script mede a latência (informativo), cria/remove um usuário de teste,
exercita matéria/baralho/flashcard, roda um passo de concorrência leve
(padrão 2 threads x 1 iteração; ajuste com `--threads N --iter N` — rodando do
Brasil, cargas maiores levam muitos minutos só pela latência, não é travamento), confere que a exclusão do usuário não deixa linhas
e **testa atomicidade**: grava uma linha dentro de uma transação, força uma
exceção e confere que a linha NÃO persistiu. Imprime `PASS` ou `FAIL`.

**Se o passo de atomicidade der FAIL, NÃO faça o deploy**: significa que o
driver confirmou o comando antes do commit (autocommit por comando), e as
exclusões em cascata (LGPD) e a gravação em lote podem ficar parciais. Ele não imprime o token. Só avance se o resultado
for PASS. Depois, apague as variáveis do terminal (`unset TURSO_AUTH_TOKEN`).

## 4. Configurar o Render

1. Render → serviço do backend → **Environment**.
2. Adicione `TURSO_DATABASE_URL` (URL do banco de produção) e
   `TURSO_AUTH_TOKEN` (marque como secreta/secret, se houver a opção).
3. Salve e faça o deploy. Com as duas variáveis presentes o backend usa o
   Turso; sem elas, usa SQLite local.

## 5. Verificar

Com um usuário admin (`ADMIN_USER_IDS`), chame `GET /admin/status` com o JWT:
deve retornar `"backend": "turso"` e `location` com apenas o **host** do
banco (não a URL completa; nunca o token),
`db_size_bytes: null` (o arquivo não é local) e `users_count` coerente.
Confira também um cadastro/login reais e que os dados sobrevivem a um novo
deploy/reinício do serviço.

## 6. Backup

- Pela API: defina `ADMIN_BACKUP_ENABLED=1` e chame `GET /admin/backup` como
  admin; baixa um arquivo `.db` (SQLite) com todas as tabelas. Desative a env
  depois de usar.
- Pela CLI do Turso (confira o comando na documentação do Turso, não
  verificado aqui): `turso db shell studex-prod .dump > backup.sql`.
- O backup contém **todos os dados pessoais**: guarde criptografado e fora do
  repositório, e apague quando não for mais necessário.
- Faça um backup antes de cada mudança grande e verifique que o arquivo abre
  (`sqlite3 backup.db "SELECT COUNT(*) FROM users"`).

## 7. Rollback

Remova `TURSO_DATABASE_URL` e `TURSO_AUTH_TOKEN` do Render e faça o deploy: o
backend volta para o SQLite local. Atenção: esse SQLite é **efêmero** no plano
free (começa vazio a cada deploy) e **não** contém os dados que estavam no
Turso. Para voltar com dados, restaure um backup no disco/serviço escolhido.
Os dados no Turso permanecem lá até serem apagados por você.

## 8. LGPD

- O Turso passa a armazenar dados pessoais (nome, e-mail, hash de senha,
  conteúdo de estudo) como **operador/subprocessador** terceirizado. Revise o
  DPA (acordo de tratamento de dados) e a política de privacidade do Turso e
  registre isso na sua política de privacidade e no registro de operações.
- Verifique a região escolhida: se estiver fora do Brasil, trata-se de
  transferência internacional de dados; confirme a base legal/garantias
  exigidas (arts. 33 e seguintes da LGPD).
- Tokens e URLs com credenciais são segredos: só em variáveis de ambiente do
  Render, nunca no Git. Em caso de vazamento, revogue o token imediatamente.
- Backups seguem as mesmas regras (criptografia, retenção mínima, exclusão).
- Ao excluir um usuário, os dados somem do Turso, mas podem permanecer em
  backups antigos: defina um prazo de retenção para eles.
