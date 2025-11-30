# Padrões de Código

## Princípios Gerais

1. **Clean Code**: Código legível é mais importante que código "esperto"
2. **DRY**: Don't Repeat Yourself
3. **SOLID**: Seguir os princípios SOLID
4. **KISS**: Keep It Simple, Stupid

## Python

### Formatação
- Usar **Black** com linha máxima de 88 caracteres
- Usar **isort** para ordenar imports
- Usar **flake8** para linting

### Type Hints
Sempre usar type hints em funções:

```python
def calculate_total(items: list[Item], discount: float = 0.0) -> Decimal:
    ...
```

### Docstrings
Usar formato Google:

```python
def process_order(order_id: UUID) -> Order:
    """Process an order and update its status.

    Args:
        order_id: The unique identifier of the order.

    Returns:
        The updated Order object.

    Raises:
        OrderNotFoundError: If the order doesn't exist.
    """
```

### Nomenclatura
- **Classes**: PascalCase (`UserService`, `OrderRepository`)
- **Funções/Métodos**: snake_case (`get_user_by_id`, `calculate_total`)
- **Constantes**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Variáveis**: snake_case (`user_count`, `total_amount`)

## TypeScript/React

### Formatação
- Usar **Prettier** com configuração padrão
- Usar **ESLint** com regras do Airbnb

### Componentes
- Preferir componentes funcionais com hooks
- Props devem ter interface definida
- Usar destructuring nas props

```typescript
interface UserCardProps {
  user: User;
  onEdit: (id: string) => void;
}

export const UserCard: React.FC<UserCardProps> = ({ user, onEdit }) => {
  // ...
};
```

## Git

### Branches
- `main`: Produção
- `develop`: Desenvolvimento
- `feature/XXX-descricao`: Novas features
- `bugfix/XXX-descricao`: Correções
- `hotfix/XXX-descricao`: Correções urgentes

### Commits
Usar Conventional Commits:

```
feat: add user authentication
fix: resolve login timeout issue
docs: update API documentation
refactor: simplify order processing
test: add unit tests for UserService
```

### Pull Requests
- Título descritivo
- Descrição com contexto e screenshots se aplicável
- Linkar issue relacionada
- Mínimo 1 aprovação para merge

## Testes

### Cobertura Mínima
- Unitários: 80%
- Integração: 60%

### Nomenclatura
```python
def test_should_create_user_when_valid_data():
    ...

def test_should_raise_error_when_email_invalid():
    ...
```

## Code Review

### Checklist do Revisor
- [ ] Código segue os padrões
- [ ] Testes adequados
- [ ] Sem secrets hardcoded
- [ ] Performance aceitável
- [ ] Documentação atualizada
