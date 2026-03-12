# Runbook Operacional Ansible

Idioma: **Português (BR)** | [English](en/ansible_ops_runbook.md)

Este runbook descreve a instalação inicial oficial do ATS em ambiente remoto com Ansible.

Baseline suportado nesta entrega:

- Ubuntu 24.04 LTS
- single-host
- Docker rootless com usuário dedicado de serviço
- imagem pública em GHCR público

## Pré-requisitos

1. Estação de operação com Ansible instalado.
1. Acesso SSH ao host remoto com usuário que tenha `sudo`.
1. Host alvo em Ubuntu 24.04 LTS.
1. Repositório clonado localmente com o diretório `ansible/` presente.
1. Inventário e variáveis preenchidos antes de executar playbooks.

## Acesso ao dashboard por domínio

Para uso real do dashboard web, é necessário publicar o endpoint local do `bot-api`
(`http://127.0.0.1:8000`) por um domínio do hospital.

Opções suportadas nesta fase:

- reverse proxy (por exemplo, Nginx/Caddy) encaminhando para `127.0.0.1:8000`.
- túnel Cloudflare (Cloudflare Tunnel) apontando para `http://127.0.0.1:8000`.

Recomendação operacional:

- usar HTTPS no domínio público.
- não expor diretamente porta de loopback sem camada de publicação controlada.

## Instalação mobile do dashboard (PWA)

Pré-requisitos para instalação em dispositivo:

- dashboard publicado em domínio HTTPS válido;
- rota inicial funcional em `/dashboard/cases`;
- autenticação web por sessão ativa para abertura direta no dashboard.

### Android (Chrome)

1. Abrir `https://<dominio>/dashboard/cases` e autenticar quando necessário.
2. No Chrome, usar o prompt de instalação (quando exibido) ou menu `Instalar app`.
3. Confirmar nome e ícone do app na tela inicial do Android.
4. Abrir o app instalado e validar execução em modo `standalone` (sem barra de URL).
5. Confirmar abertura inicial em `/dashboard/cases`.
6. Com sessão expirada/ausente, validar redirecionamento para `/login`.

### iOS (Safari)

1. Abrir `https://<dominio>/dashboard/cases` no Safari.
2. Usar `Compartilhar` -> `Adicionar à Tela de Início`.
3. Confirmar nome e ícone do atalho criado.
4. Abrir pela tela inicial e validar contexto standalone do Safari.
5. Confirmar abertura inicial em `/dashboard/cases`.
6. Com sessão expirada/ausente, validar redirecionamento para `/login`.

### Limitação operacional explícita

O dashboard instalado como PWA **não oferece suporte offline**.

Com a rede indisponível:

- o app não deve exibir fallback offline com conteúdo clínico cacheado;
- falhas de carregamento devem seguir semântica normal de erro de rede do browser.

## Inventário mínimo

Crie `ansible/inventory/hosts.yml`:

```yaml
all:
  hosts:
    ats-prod-01:
      ansible_host: 203.0.113.10
      ansible_user: ubuntu
```

Preencha variáveis obrigatórias em `ansible/host_vars/ats-prod-01.yml`:

```yaml
ats_runtime_env_required:
  DATABASE_URL: "postgresql+asyncpg://ats:<senha>@127.0.0.1:5432/ats"
  ROOM1_ID: "!room1:example.org"
  ROOM2_ID: "!room2:example.org"
  ROOM3_ID: "!room3:example.org"
  MATRIX_HOMESERVER_URL: "https://matrix.example.org"
  MATRIX_BOT_USER_ID: "@ats-bot:example.org"
  MATRIX_ACCESS_TOKEN: "<token>"
  WEBHOOK_PUBLIC_URL: "https://ats.example.org/widget"
  WEBHOOK_HMAC_SECRET: "<segredo>"
```

Opcional para bootstrap do primeiro admin:

```yaml
ats_runtime_env_optional:
  BOOTSTRAP_ADMIN_EMAIL: "admin@example.org"
  BOOTSTRAP_ADMIN_PASSWORD: "<senha-forte>"
```

## Comandos oficiais de instalação inicial

1. Executar bootstrap do host (dependências, usuário de serviço e Docker rootless):

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/bootstrap.yml
```

1. Executar deploy inicial com tag explícita:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deploy.yml \
  -e ats_runtime_image_tag=v1.0.0
```

1. Resultado esperado:

- serviços `bot-api`, `bot-matrix` e `worker` iniciados.
- configuração de runtime renderizada em `{{ ats_runtime_root }}` no host remoto.
- playbook finalizado sem falhas.

## Agendamento gerenciado do scheduler da Room-4

O cron do resumo periódico da Room-4 é gerenciado pelo Ansible durante `deploy`,
`upgrade` e `rollback`, sempre no usuário de serviço (`ats`).

Variáveis operacionais (em `ansible/host_vars/<host>.yml` quando precisar sobrescrever defaults):

```yaml
ats_room4_scheduler_cron_enabled: true
ats_room4_scheduler_cron_timezone: "UTC"
ats_room4_scheduler_cron_minute: "0"
ats_room4_scheduler_cron_hour: "10,16,22"
ats_room4_scheduler_cron_log_file: "/home/ats/augmented-triage-system/logs/room4-scheduler-cron.log"
```

Observação: no baseline atual, o host roda em UTC; os horários `10,16,22` em UTC
correspondem a `07:00, 13:00 e 19:00 em America/Bahia`.

Comando gerenciado no cron:

- `docker compose ... run --rm --no-deps worker uv run python -m apps.scheduler.main`

Checklist pós-deploy para validar agendamento e execução:

1. Verificar entradas gerenciadas no crontab do usuário de serviço:

```bash
crontab -u ats -l | grep -E "ATS Room-4 Scheduler|CRON_TZ|XDG_RUNTIME_DIR|DOCKER_HOST"
```

1. Verificar logs do scheduler:

```bash
tail -n 50 /home/ats/augmented-triage-system/logs/room4-scheduler-cron.log
```

1. Verificar evidência de enfileiramento `post_room4_summary`:

```bash
docker compose \
  --project-name augmented-triage-system \
  --file /home/ats/augmented-triage-system/docker-compose.yml \
  exec -T postgres psql -U triage -d triage \
  -c "SELECT job_id, job_type, status, created_at FROM jobs WHERE job_type = 'post_room4_summary' ORDER BY job_id DESC LIMIT 5;"
```

### Checklist de coerência entre timezone do app e cron

1. Verificar no arquivo de runtime (`.env`) os valores de aplicação:

```bash
grep -E "SUPERVISOR_SUMMARY_TIMEZONE|SUPERVISOR_SUMMARY_CUTOFF_HOURS" /home/ats/augmented-triage-system/.env
```

1. Verificar no crontab do usuário `ats` os valores de cron e horário:

```bash
crontab -u ats -l | grep -E "CRON_TZ|ATS Room-4 Scheduler"
```

1. Critério de sucesso operacional:

- `SUPERVISOR_SUMMARY_TIMEZONE` e `SUPERVISOR_SUMMARY_CUTOFF_HOURS` devem representar os mesmos cortes usados no cron.
- No baseline atual, isso significa `SUPERVISOR_SUMMARY_TIMEZONE=America/Bahia`, `SUPERVISOR_SUMMARY_CUTOFF_HOURS=7,13,19` e cron UTC em `10,16,22`.

## Política de pull de imagem no deploy/upgrade

Política padrão atual do runtime:

- `ats_runtime_pull_policy: "always"`

Implicações operacionais:

- o deploy/upgrade sempre tenta baixar a imagem da tag alvo no registry;
- o comportamento não depende de remover imagem local da tag antes do `pull`.

Observação sobre limpeza de imagem:

- a remoção prévia da imagem alvo é executada apenas em modo `missing` (best-effort);
- no baseline (`always`), essa remoção condicional fica inativa.

## Fluxo oficial de upgrade

1. Defina a nova tag alvo (não usar `latest`):

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/upgrade.yml \
  -e ats_runtime_image_tag=v1.0.1
```

1. Resultado esperado:

- serviços continuam em execução após atualização.
- validação pós-deploy do playbook executa `Validate all runtime services are running after upgrade`.
- playbook finalizado sem falhas.

## Fluxo oficial de rollback

1. Defina a tag estável anterior para retorno:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/rollback.yml \
  -e ats_runtime_rollback_image_tag=v1.0.0
```

1. Resultado esperado:

- serviços retornam para a versão estável definida no rollback.
- validação pós-rollback do playbook executa `Validate all runtime services are running after rollback`.
- playbook finalizado sem falhas.

## Troubleshooting de primeiro nível

1. Falha por variável obrigatória ausente no bootstrap:

- sintoma: playbook falha com mensagem contendo `Required runtime variable`.
- ação imediata: revisar `ansible/host_vars/<host>.yml` e preencher todas as chaves de `ats_runtime_env_required`.
- repetir comando oficial:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/bootstrap.yml
```

1. Falha por tag inválida (`latest`) em deploy/upgrade:

- sintoma: playbook falha com `Explicit runtime image tag is required.`.
- ação imediata: definir tag explícita versionada em `ats_runtime_image_tag` e executar novamente.

1. Falha no gate pós-deploy:

- sintoma: erro com `Deploy approval gate failed.`.
- ação imediata: validar status dos serviços no host e corrigir configuração de runtime antes de nova execução.
- repetir o comando do playbook correspondente (`deploy.yml`, `upgrade.yml` ou `rollback.yml`).

1. Cron da Room-4 configurado, mas execução falha:

- sintoma: entrada `ATS Room-4 Scheduler` existe no `crontab -u ats -l`, porém sem enfileiramento recente de `post_room4_summary`.
- ação imediata:
  - validar variáveis de ambiente no cron (`CRON_TZ`, `XDG_RUNTIME_DIR`, `DOCKER_HOST`);
  - validar alcance do compose no contexto rootless com `docker compose ... ps` no usuário `ats`;
  - revisar `ats_room4_scheduler_cron_log_file` para erro de comando/permissão.
- se persistir após ajuste e novo `deploy/upgrade/rollback`, escalar para desenvolvimento.

## Limites de escalonamento para desenvolvimento

Escalonar para desenvolvimento quando:

- erro persistir após correção de inventário/variáveis e nova execução completa do playbook.
- falha indicar possível bug de automação (ex.: role com comportamento inconsistente entre execuções idempotentes).
- falha de validação pós-deploy não for resolvida com ajuste operacional de primeiro nível.

Incluir no chamado para escalonar para desenvolvimento:

- comando executado e horário.
- host alvo e tag usada (`ats_runtime_image_tag` ou `ats_runtime_rollback_image_tag`).
- trecho relevante do erro retornado pelo Ansible.
