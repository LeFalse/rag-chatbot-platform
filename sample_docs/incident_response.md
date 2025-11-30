# Resposta a Incidentes

## Classificação de Severidade

| Severidade | Descrição | Tempo de Resposta | Exemplos |
|------------|-----------|-------------------|----------|
| **SEV1** | Sistema totalmente indisponível | 15 minutos | Site fora do ar, dados corrompidos |
| **SEV2** | Funcionalidade crítica afetada | 1 hora | Pagamentos falhando, login quebrado |
| **SEV3** | Funcionalidade secundária afetada | 4 horas | Relatórios lentos, notificações atrasadas |
| **SEV4** | Problema menor | 24 horas | Bug visual, erro de texto |

## Processo de Resposta

### 1. Detecção
- Alerta do PagerDuty
- Reclamação de cliente
- Monitoramento interno

### 2. Triagem (primeiros 5 minutos)
- Confirmar o problema
- Classificar severidade
- Notificar canal #incidents
- Acionar on-call se SEV1/SEV2

### 3. Investigação
- Verificar dashboards do Grafana
- Analisar logs no Loki
- Identificar mudanças recentes (deploys)
- Correlacionar com eventos externos

### 4. Mitigação
- Aplicar fix temporário se possível
- Considerar rollback
- Escalar recursos se necessário
- Comunicar status a cada 30 minutos

### 5. Resolução
- Implementar correção definitiva
- Validar em staging
- Deploy com monitoramento intensivo

### 6. Post-Mortem
- Documentar timeline
- Identificar root cause
- Definir ações preventivas
- Compartilhar aprendizados

## Runbooks

### Alta Latência no API Gateway
1. Verificar métricas de CPU/memória dos pods
2. Checar conexões com banco de dados
3. Analisar slow queries no RDS
4. Verificar rate limiting atingido
5. Escalar horizontalmente se necessário

### Falha na Conexão com Banco
1. Verificar status do RDS na AWS Console
2. Checar connection pool nos serviços
3. Validar credentials nos secrets
4. Verificar network policies
5. Reiniciar pods se necessário

### Fila de Mensagens Acumulando
1. Verificar consumers ativos
2. Checar logs de erro nos consumers
3. Analisar taxa de processamento
4. Escalar consumers temporariamente
5. Investigar mensagens problemáticas

## Contatos de Emergência

| Papel | Nome | Telefone | Horário |
|-------|------|----------|---------|
| On-call Primário | Rotativo | PagerDuty | 24/7 |
| On-call Secundário | Rotativo | PagerDuty | 24/7 |
| Tech Lead | João Silva | +55 11 99999-1111 | Emergências |
| DevOps Lead | Maria Santos | +55 11 99999-2222 | Emergências |
| CTO | Roberto Lima | +55 11 99999-3333 | SEV1 apenas |

## Comunicação Externa

Para incidentes que afetam clientes:
1. Atualizar status page (status.empresa.com)
2. Notificar Customer Success
3. Preparar comunicado se necessário
4. Documentar para relatório mensal
