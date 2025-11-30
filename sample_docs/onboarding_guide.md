# Guia de Onboarding - Technical Team

## Bem-vindo ao Time!

Este documento contém as informações essenciais para novos membros do time técnico.

## Ferramentas Utilizadas

### Desenvolvimento
- **IDE**: VS Code com extensões recomendadas (Python, Docker, GitLens)
- **Versionamento**: Git com GitHub
- **Containers**: Docker e Docker Compose
- **CI/CD**: GitHub Actions

### Comunicação
- **Chat**: Slack (canais: #tech-team, #deployments, #incidents)
- **Reuniões**: Google Meet
- **Documentação**: Confluence

### Monitoramento
- **Logs**: Grafana Loki
- **Métricas**: Prometheus + Grafana
- **Alertas**: PagerDuty

## Configuração do Ambiente Local

1. Clonar os repositórios necessários
2. Instalar Docker Desktop
3. Copiar arquivo `.env.example` para `.env`
4. Executar `docker compose up -d`
5. Acessar http://localhost:3000

## Acesso aos Sistemas

Solicitar acesso ao Tech Lead para:
- GitHub (organização)
- AWS Console (role de desenvolvedor)
- Banco de dados (read-only para produção)
- VPN corporativa

## Primeiro Sprint

Na primeira semana, você irá:
1. Configurar ambiente de desenvolvimento
2. Fazer pair programming com um membro sênior
3. Resolver uma issue marcada como "good first issue"
4. Participar das cerimônias do Scrum

## Contatos Importantes

- **Tech Lead**: João Silva (joao.silva@empresa.com)
- **DevOps**: Maria Santos (maria.santos@empresa.com)
- **Product Owner**: Carlos Lima (carlos.lima@empresa.com)
