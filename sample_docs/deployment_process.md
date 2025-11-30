# Processo de Deployment

## Ambientes

| Ambiente | URL | Branch | Deploy |
|----------|-----|--------|--------|
| Development | dev.empresa.com | develop | Automático |
| Staging | staging.empresa.com | release/* | Manual |
| Production | app.empresa.com | main | Manual com aprovação |

## Fluxo de Deploy

### 1. Development
- Push para branch `develop` dispara deploy automático
- Testes unitários e de integração são executados
- Deploy em ambiente de desenvolvimento

### 2. Staging
- Criar branch `release/v1.x.x` a partir de `develop`
- Executar pipeline de staging manualmente
- QA realiza testes de aceitação
- Correções são feitas na branch de release

### 3. Production
- Merge da branch de release para `main`
- Abrir PR com changelog
- Obter aprovação de pelo menos 2 revisores
- Tech Lead executa o deploy via GitHub Actions

## Checklist Pré-Deploy

- [ ] Todos os testes passando
- [ ] Code review aprovado
- [ ] Migrations de banco testadas
- [ ] Feature flags configuradas
- [ ] Rollback plan documentado
- [ ] Comunicação no canal #deployments

## Rollback

Em caso de problemas:

1. Identificar a versão anterior estável
2. Executar workflow de rollback no GitHub Actions
3. Comunicar no canal #incidents
4. Documentar o incidente no Confluence

## Horários de Deploy

- **Produção**: Segunda a Quinta, 10h-16h
- **Evitar**: Sextas-feiras e vésperas de feriado
- **Emergências**: Qualquer horário com aprovação do Tech Lead

## Monitoramento Pós-Deploy

Após cada deploy em produção:
1. Verificar dashboards no Grafana (15 minutos)
2. Monitorar logs de erro no Loki
3. Validar métricas de negócio
4. Confirmar sucesso no canal #deployments
