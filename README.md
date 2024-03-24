# Postgresql config helper для 1С Предприятие
Скрипт, изменяющий конфигурацию PostgreSQL согласно [рекомендациями из документации 1С](https://its.1c.ru/db/metod8dev#content:5866:hdoc)

# Использование

## Показать встроенную справку

```powershell
1cv8_postgres_helper.exe --help
```

## Наиболее простой вариант

```powershell
1cv8_postgres_helper.exe --config postgresql.example.conf --mem 32GB
```

## Все доступные аргументы

```powershell
1cv8_postgres_helper.exe --config postgresql.example.conf --mem 32GB --cpu 8 --storage ssd --disable-synchronous-commit --enable-group-commit --no-backup
```
