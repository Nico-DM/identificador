# Diagrama de Gantt

Cronograma de la PPS _Identificador de Artistas_. Formato Mermaid (se renderiza en GitHub).

**Hitos de referencia**

| Hito                       | Fecha                                       |
| -------------------------- | ------------------------------------------- |
| Inicio del proyecto        | Junio 2025                                  |
| Primera entrega (CLI)      | Agosto 2025                                 |
| Segunda entrega (web)      | 3 de junio de 2026                          |
| Devolución segunda entrega | 18 de agosto de 2026                        |
| Instancia extraordinaria   | Desde agosto 2026 (sin fecha límite formal) |

---

## Vista general

```mermaid
gantt
    title Identificador de Artistas — PPS
    dateFormat  YYYY-MM-DD
    axisFormat  %b %Y

    section Primera etapa (CLI)
    Investigación SerpAPI           :a1, 2025-06-09, 2025-06-15
    Implementación SerpAPI (Lens)   :a2, 2025-06-16, 2025-06-29
    Obtención de fechas             :a3, 2025-06-30, 2025-08-10
    Entrega 1                       :milestone, m1, 2025-08-15, 0d

    section Segunda etapa (web)
    Frontend Next.js + TypeScript   :b1, 2025-09-01, 2026-03-15
    Backend FastAPI + workers       :b2, 2025-10-01, 2026-04-30
    Supabase / storage / deploy     :b3, 2026-02-01, 2026-05-31
    Entrega 2                       :milestone, m2, 2026-06-03, 0d

    section Instancia extraordinaria
    Devolución 2ª entrega           :milestone, m3, 2026-08-18, 0d
    Strategy + google_reverse_image :c1, 2026-08-19, 2026-08-27
    Selenium en Docker / logging    :c2, 2026-08-27, 2026-08-28
    Tests + dataset formal          :c3, 2026-09-01, 2026-09-02
    Fallbacks Bing/Yandex           :c4, 2026-09-03, 2026-09-08
    Docs oficiales (docs/)          :c5, 2026-09-16, 2026-09-20
    Mejora métricas dataset         :c6, 2026-09-16, 2026-09-30
```

---

## Detalle por etapa

### Primera etapa (junio–agosto 2025)

Tomado del Gantt de la primera entrega:

| Tarea                                | Inicio    | Fin       |
| ------------------------------------ | --------- | --------- |
| Investigación SerpAPI                | 9/6/2025  | 15/6/2025 |
| Implementación SerpAPI (Google Lens) | 16/6/2025 | 29/6/2025 |
| Obtención de fecha de publicaciones  | 30/6/2025 | 10/8/2025 |

Producto: CLI Python + SerpAPI Google Lens.

### Segunda etapa (hasta 3/6/2026)

Evolución a arquitectura web: Next.js (Vercel), FastAPI (Render), Supabase, flujo asíncrono con polling, scoring y scraping estático. Entrega el **3 de junio de 2026**.

### Instancia extraordinaria (desde 18/8/2026)

Respuesta a la devolución: motor `google_reverse_image`, patrón Strategy, fallbacks Bing/Yandex, Selenium operativo en Docker, caché en DB, tests, dataset documentado y documentación formal en `docs/`.

---

## Tabla compacta (accesible sin render Mermaid)

| Fase                           | Periodo             | Entregable principal       |
| ------------------------------ | ------------------- | -------------------------- |
| CLI + Lens                     | jun–ago 2025        | Primera entrega            |
| Web full-stack                 | sep 2025 – jun 2026 | Segunda entrega (3/6/2026) |
| Contingencia motores + calidad | ago–sep 2026        | Instancia extraordinaria   |
