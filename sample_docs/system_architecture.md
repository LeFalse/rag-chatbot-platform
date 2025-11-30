# Arquitetura do Sistema

## Visão Geral

Nossa plataforma utiliza arquitetura de microserviços com os seguintes componentes principais:

```
[Cliente Web] → [API Gateway] → [Microserviços] → [Databases]
                     ↓
              [Auth Service]
```

## Serviços Principais

### API Gateway (Kong)
- Roteamento de requisições
- Rate limiting: 1000 req/min por usuário
- Autenticação JWT
- Cache de respostas (Redis)

### Auth Service
- Autenticação OAuth2 / OpenID Connect
- Gerenciamento de sessões
- Integração com SSO corporativo
- Tokens JWT com expiração de 1 hora

### User Service
- CRUD de usuários
- Perfis e permissões
- Banco: PostgreSQL
- Cache: Redis

### Order Service
- Processamento de pedidos
- Integração com pagamentos
- Filas: RabbitMQ
- Banco: PostgreSQL

### Notification Service
- Email (SendGrid)
- Push notifications (Firebase)
- SMS (Twilio)
- Filas assíncronas

## Infraestrutura

### Cloud Provider: AWS
- **Compute**: EKS (Kubernetes)
- **Database**: RDS PostgreSQL
- **Cache**: ElastiCache Redis
- **Storage**: S3
- **CDN**: CloudFront

### Kubernetes
- Cluster com 3 nodes (produção)
- Autoscaling: 2-10 pods por serviço
- Ingress: NGINX
- Service Mesh: Istio

## Comunicação entre Serviços

- **Síncrona**: REST APIs via HTTP/2
- **Assíncrona**: RabbitMQ para eventos
- **Padrão**: Event-driven architecture

## Segurança

- TLS 1.3 em todas as conexões
- Secrets gerenciados via AWS Secrets Manager
- Network policies no Kubernetes
- WAF no API Gateway
- Logs de auditoria em todas as operações

## SLAs

| Métrica | Target |
|---------|--------|
| Disponibilidade | 99.9% |
| Latência P95 | < 200ms |
| Latência P99 | < 500ms |
| Recovery Time | < 15 min |
