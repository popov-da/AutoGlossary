# Схемы AutoGlossary

## Master termbase

Основной внутренний файл: `data/termbase.csv`.

| Поле | Обязательное | Описание |
|---|---:|---|
| `source` | да | Английский термин или фраза без конечной точки |
| `target_preferred` | да | Предпочтительный русский эквивалент |
| `status` | да | `candidate`, `reviewed`, `approved` или `deprecated` |
| `category` | да | Тематическая категория |
| `source_id` | да | Обезличенный идентификатор источника или корпуса |
| `confidence` | да | `high`, `medium` или `low` |
| `source_document` | да | Публичное имя domain-файла либо метка корпуса без имени закрытого `.dita` |
| `term_type` | да | Тип: `term`, `component`, `procedure`, `heading`, `abbreviation` и т. п. |
| `alternate_targets` | нет | Альтернативные RU-варианты, обнаруженные при merge |

Master генерируется. Редактировать его напрямую не следует: изменения вносятся в domain-файлы `data/*.csv` и `imports/*.csv`, затем выполняется rebuild.

## Domain CSV

Минимальные обязательные поля:

```text
source,target_preferred,status
```

Допускаются master-метаданные: `category`, `source_id`, `confidence`, `source_document`, `term_type`, `alternate_targets`.

Во входных domain-файлах допустим статус `rejected`; такие строки не попадают в master и consumer export.

## Consumer CSV

Основной внешний файл: `exports/consumer-glossary.csv`.

Схема фиксирована и содержит **ровно три колонки**:

```text
source,target_preferred,status
```

Лишние колонки запрещены. Допустимые статусы:

- `candidate`;
- `reviewed`;
- `approved`;
- `deprecated`.

`rejected` не экспортируется.

## Инварианты

1. Один `source` — одна строка в master и consumer export; проверка дублей выполняется по `strip + casefold`.
2. `source` хранится без конечной точки у словарной формы.
3. `approved` назначается только после редакторского решения и не перезаписывается `candidate` при rebuild.
4. Конфликты разных `target_preferred` фиксируются в `reports/conflicts.csv` и в `alternate_targets`.
5. Полные имена закрытых `.dita` не коммитятся в генерируемые файлы.
6. Короткие неоднозначные сокращения добавляются только после ручной оценки ложных срабатываний.
7. Consumer сопоставляет термины по границам слов и longest-match; поэтому предпочтительны полные устойчивые фразы.

## Кодировка

Все CSV записываются в UTF-8 с BOM (`utf-8-sig`) для совместимости с потребителем и Excel. Разделитель — запятая; поля с запятыми экранируются стандартными правилами CSV.

## Pipeline

```bash
python scripts/rebuild_termbase.py
python scripts/export_consumer.py
python scripts/validate.py
```
