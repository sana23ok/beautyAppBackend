-- Розклад майстра в БД зберігається в ДВОХ місцях:
--
-- 1) masters_master — «шаблон» на тиждень (поля monday_hours … sunday_hours).
-- 2) masters_masterweektimetable — окремі рядки на кожен понеділок (week_start),
--    якщо для конкретного тижня години відрізняються від шаблону.
--
-- SQLite / PostgreSQL (синтаксис SELECT сумісний).

-- ── 1. Базовий розклад (шаблон) по кожному майстру ─────────────────────────
SELECT
    id,
    name,
    monday_hours,
    tuesday_hours,
    wednesday_hours,
    thursday_hours,
    friday_hours,
    saturday_hours,
    sunday_hours
FROM masters_master
ORDER BY id;

-- ── 2. Покриття по тижнях (MasterWeekTimetable) ─────────────────────────────
SELECT
    w.id,
    w.master_id,
    m.name AS master_name,
    w.week_start,
    w.monday_hours,
    w.tuesday_hours,
    w.wednesday_hours,
    w.thursday_hours,
    w.friday_hours,
    w.saturday_hours,
    w.sunday_hours,
    w.created_at,
    w.updated_at
FROM masters_masterweektimetable w
JOIN masters_master m ON m.id = w.master_id
ORDER BY w.master_id, w.week_start;

-- ── 3. Лише рядки з непорожніми годинами (фільтр для швидкої перевірки) ─────
SELECT w.*, m.name AS master_name
FROM masters_masterweektimetable w
JOIN masters_master m ON m.id = w.master_id
WHERE
    TRIM(COALESCE(w.monday_hours, '')) != ''
    OR TRIM(COALESCE(w.tuesday_hours, '')) != ''
    OR TRIM(COALESCE(w.wednesday_hours, '')) != ''
    OR TRIM(COALESCE(w.thursday_hours, '')) != ''
    OR TRIM(COALESCE(w.friday_hours, '')) != ''
    OR TRIM(COALESCE(w.saturday_hours, '')) != ''
    OR TRIM(COALESCE(w.sunday_hours, '')) != ''
ORDER BY w.master_id, w.week_start;
