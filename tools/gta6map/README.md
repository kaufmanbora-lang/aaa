# Карта GTA 6 (папка `docs/`)

Статический сайт для GitHub Pages: интерактивная фан-карта штата Леонида.
Сайт не требует сборки — всё, что лежит в `docs/`, отдаётся как есть.

## Публикация

`Settings → Pages → Build and deployment → Source: Deploy from a branch`,
ветка с этим кодом, папка `/docs`. Адрес: `https://<пользователь>.github.io/<репозиторий>/`.

## Что откуда

| Что | Источник | Лицензия / условия |
| --- | --- | --- |
| Тайлы карты `docs/tiles`, ориентиры, игровые фото `docs/photos` | [gtadb.org](https://gtadb.org) ([репозиторий](https://github.com/rolux/gtadb.org)) и участники | данные CC BY 4.0 |
| Положение предметов, транспорта, магазинов, активностей | интерактивная карта IGN / MapGenie | используются только факты (названия, координаты, числовые параметры); тексты подсказок написаны заново |
| Точки миссий и банков | [PowerPyx](https://www.powerpyx.com/) через [GTA-6-Interactive-Map-and-Loot-Tracker](https://github.com/theihtishaam/GTA-6-Interactive-Map-and-Loot-Tracker) | MIT |
| Уникальное оружие, редкие машины, секреты | гайды и находки игроков, см. `research/*.json` (в каждой записи есть ссылки) | — |
| Значки | Material Design Icons (`@mdi/svg`) | Apache 2.0 |
| Движок карты | Leaflet 1.9.4 | BSD-2-Clause |

Фото из слива 2022 года (в GTADB помечены тегами L1…L8) не публикуются — `build_photos.py` их пропускает.
Grand Theft Auto, карта и изображения из игры принадлежат Rockstar Games / Take-Two; проект неофициальный и некоммерческий.

## Пересборка данных

```bash
GTADB=/path/gtadb.org IGN=/path/ign-data PPX=/path/loot-tracker TR=tools/gta6map/hints tools/gta6map/build.sh
python3 tools/gta6map/build_tiles.py  /path/gtadb.org   # docs/tiles (+ индекс существующих тайлов docs/data/tiles.json пересоздаётся отдельно)
python3 tools/gta6map/build_photos.py /path/gtadb.org   # docs/photos
python3 tools/gta6map/build_icons.py  node_modules/@mdi/svg/svg
```

- `build_data.py` — сводит источники в `docs/data/markers.json`: переводит координаты IGN/MapGenie в игровые метры
  (тот же кадр 32768 м, что у GTADB, со сдвигом 950×200 px при 4 м/px — проверено корреляцией изображений),
  назначает категории и цвет редкости, считает район и ближайший ориентир, сверяет точки между источниками.
- `make_extras.py` — привязывает находки из `research/*.json` к уже известным местам; то, что привязать нельзя,
  попадает в `extras_skipped.json` и показывается на сайте списком «не нанесено на карту».
- `hints/out_*.json` — подсказки «где лежит» на русском.

Уровни проверки в карточке: `3` — совпало в двух независимых источниках, `2` — один надёжный источник,
`1`/`0` — не подтверждено или место примерное.
