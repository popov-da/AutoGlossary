# AutoGlossary

Открытая англо-русская терминологическая база для автомобильной технической документации и машинного перевода.

## Текущее состояние

Master-база собирается из domain- и import-CSV и содержит **более 2 000 терминов и устойчивых фраз**. Точное количество выводит `scripts/rebuild_termbase.py` при каждой сборке.

Основной фокус:

- сервисные и ремонтные руководства;
- кузовной ремонт и сварка;
- двигатель, трансмиссия и ходовая часть;
- электрооборудование и диагностика;
- реальные OEM-корпуса N155/N165;
- EV, ADAS, AUTOSAR и автомобильные протоколы.

## Канонический pipeline

```bash
python scripts/rebuild_termbase.py
python scripts/export_consumer.py
python scripts/validate.py
```

Порядок работы:

1. редактировать или добавлять domain CSV в `data/` либо `imports/`;
2. собрать единый master-файл `data/termbase.csv`;
3. сформировать consumer exports;
4. выполнить полную валидацию.

## Основные артефакты

- [`data/termbase.csv`](data/termbase.csv) — master termbase с метаданными;
- [`exports/consumer-glossary.csv`](exports/consumer-glossary.csv) — основной внешний CSV для машинного перевода;
- [`exports/consumer-body-repair.csv`](exports/consumer-body-repair.csv) — кузов, сварка и сервисные операции;
- [`exports/consumer-n155-n165.csv`](exports/consumer-n155-n165.csv) — термины из OEM-корпусов N155/N165;
- [`exports/consumer-mechanical.csv`](exports/consumer-mechanical.csv) — механика без перегруза ADAS/EV;
- [`reports/conflicts.csv`](reports/conflicts.csv) — неразрешённые варианты перевода одного source;
- [`data/volga-pilot-approved.csv`](data/volga-pilot-approved.csv) — небольшой пилотный слой утверждённой терминологии;
- [`docs/merge-policy.md`](docs/merge-policy.md) — правила объединения и разрешения конфликтов;
- [`docs/schema.md`](docs/schema.md) — схемы master и consumer CSV.

## Контракт consumer export

`exports/consumer-glossary.csv` содержит строго три колонки:

```text
source,target_preferred,status
```

Правила:

- один `source` — одна строка, сравнение дублей по `casefold`;
- английская словарная форма хранится без конечной точки;
- допустимые статусы: `candidate`, `reviewed`, `approved`, `deprecated`;
- `rejected` не экспортируется;
- лишние master-поля в consumer CSV не попадают;
- `approved` используется только после редакторского решения.

## Статусы

| Статус | Назначение |
|---|---|
| `candidate` | Автоматически или редакторски предложенный вариант |
| `reviewed` | Проверенный вариант, ещё не включающий жёсткий контроль |
| `approved` | Утверждённый вариант для строгого контроля перевода |
| `deprecated` | Устаревший или нежелательный вариант |
| `rejected` | Допустим только во входных domain-файлах и не экспортируется |

## Сокращения

Короткие и неоднозначные сокращения добавляются только осознанно. В пилотной политике латиницей сохраняются, например, `ABS`, `OBD`, `ATF` и `VIN`; `ECU`, `TDC`, `BDC` переводятся как `ЭБУ`, `ВМТ`, `НМТ`.
