---
change_id: longest-streak
title: Najdłuższy streak jako metryka i sygnał dla AI
status: archived
created: 2026-07-04
updated: 2026-07-04
archived_at: 2026-07-04T14:43:26Z
---

## Notes

Post-MVP, mała zmiana do przećwiczenia M3L2 (`/10x-tdd`, red→green→refactor). Dodaje czystą funkcję
`longest_streak` (najdłuższa seria kolejnych dni w oknie 30 dni), wpina ją w `build_history_context`
(pole per-nawyk) i wystawia w promptcie AI (`build_messages`) jako dodatkowy ugruntowany sygnał.
Czysta logika, brak istniejącej implementacji — idealny materiał test-first.
