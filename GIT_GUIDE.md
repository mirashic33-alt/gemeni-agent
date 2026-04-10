# Git — Шпаргалка для YouTube-серии

## После каждого видео (обновить код на GitHub)

```bash
git add .
git commit -m "Episode 2: добавили голосовой ввод"
git push
```

---

## Пометить версию для видео (тег)

Делать ПОСЛЕ `git push`, в конце каждого видео:

```bash
git tag v2.0 -m "Episode 2: голосовой ввод"
git push origin v2.0
```

На GitHub зрители смогут зайти в раздел **Releases / Tags** и скачать
код именно этого видео.

---

## Полный сценарий конца видео

```bash
git add .
git commit -m "Episode 3: память агента"
git push
git tag v3.0 -m "Episode 3: память агента"
git push origin v3.0
```

---

## Если нужно вернуться к старой версии (только посмотреть)

```bash
git checkout v1.0
```

Вернуться обратно к актуальной версии:

```bash
git checkout master
```

---

## Первый раз на новом компьютере (клонировать репозиторий)

```bash
git clone https://github.com/mirashic33-alt/gemeni-agent.git
cd gemeni-agent
```

---

## Текущие теги проекта

| Тег   | Описание         |
|-------|------------------|
| v1.0  | Episode 1: базовый агент, синхронизация времени, автопрокрутка |

---

## Частые ошибки

**`error: src refspec main does not match any`**
→ Ветка называется `master`, не `main`. Используй `git push origin master`.

**`rejected: fetch first`**
→ Сначала `git pull origin master --allow-unrelated-histories`, потом `git push`.

**`remote origin already exists`**
→ Не страшно, репозиторий уже настроен. Продолжай.
