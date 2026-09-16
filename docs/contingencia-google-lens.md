# Informe técnico de contingencia — Google Lens

## 1. Contexto

En la **primera entrega** (agosto 2025) el identificador era una CLI Python que usaba **SerpAPI con motor `google_lens`** para obtener páginas candidatas a partir de una URL de imagen. Ese enfoque quedó documentado en la entrega inicial (*Documentación PPS — Identificador Artistas*).

Durante la evolución a la aplicación web y hacia la **segunda entrega** (3 de junio de 2026), se constató que los resultados de Lens dejaban de servir al objetivo del proyecto: ubicar la **publicación original** (o la aparición más temprana plausible), no “imágenes parecidas”.

La devolución del **18 de agosto de 2026** confirma el diagnóstico: Lens prioriza coincidencias semánticas / de similitud visual frente a matches exactos y fuentes históricas.

---

## 2. Cambio detectado en Google Lens

Google Lens, expuesto vía API, pasó a comportarse de forma coherente con un buscador visual basado en **embeddings de similitud**:

- Devuelve contenido **relacionado o similar**, no necesariamente la misma imagen.
- Pierde utilidad para cadenas de reposteo y para datar la primera publicación.
- La experiencia web de Google (“Find image source” / coincidencias exactas) **no se mapea 1:1** al endpoint Lens de SerpAPI usado en el proyecto.

Esto no fue un “apagón” total de la API (las llamadas seguían respondiendo), sino una **degradación funcional** respecto de RF-002…RF-005.

---

## 3. Impacto sobre los requerimientos

| Requisito | Impacto |
|-----------|---------|
| **RF-002** Búsqueda inversa | Cumplimiento formal (hay respuesta), incumplimiento semántico (candidatos poco útiles). |
| **RF-003** Candidatos | Volumen de URLs podía mantenerse, pero con bajo valor para origen artístico. |
| **RF-004 / RF-005** Fechas y ranking | El scoring operaba sobre un conjunto sesgado → fechas y “original” poco confiables. |
| **RNF-001** Precisión | El dataset no puede validar el producto si el motor primario no aporta fuentes correctas. |
| Arquitectura | Riesgo materializado: dependencia única de un proveedor externo (señalado ya en la 1ª entrega). |

No se trata de un bug local de parsing exclusivamente: el cambio es del **producto upstream**.

---

## 4. Respuesta técnica adoptada

1. **Reemplazo del primario:** `SEARCH_ENGINE=google_reverse_image` (SerpAPI), orientado a búsqueda inversa clásica por imagen.
2. **Desacoplamiento Strategy:** interfaz `SearchEngine` + factory (`search_engines/`), de modo que scoring y UI no dependan del proveedor.
3. **Fallbacks:** Bing Reverse Image y Yandex Images vía SerpAPI, fusionados con RRF cuando el primario aporta pocas URLs.
4. **Observabilidad:** logs estructurados de errores y eventos de engine (`engine_results`, `search_failed`, caché de payloads).
5. **Documentación:** este informe + [alternativas-tecnologicas.md](alternativas-tecnologicas.md).

El adaptador `google_lens` permanece disponible por configuración para comparación o rollback, pero **no es el default**.

---

## 5. Comportamiento esperado vs obtenido

| Aspecto | Esperado (diseño 1ª entrega) | Obtenido con Lens degradado | Obtenido tras contingencia |
|---------|------------------------------|-----------------------------|----------------------------|
| Tipo de match | Páginas con la misma imagen / fuente | Similares semánticos | Coincidencias de imagen vía reverse image + diversidad Bing/Yandex |
| Entrada a scraping | URLs de publicaciones reales | Muchas URLs poco relacionadas | Mejores candidatos para datar |
| Cambio de motor | Reescritura del núcleo | — | Solo config + adaptador |

---

## 6. Lecciones aprendidas

1. **Tratar APIs de búsqueda visual como componentes volátiles:** el contrato HTTP puede mantenerse mientras cambia la semántica del ranking.
2. **Diseñar puerto/adaptador desde el inicio:** el patrón Strategy redujo el costo de la migración a `google_reverse_image` y a los fallbacks.
3. **Medir con dataset fijo:** sin regresión de 10 imágenes, la degradación se discute en abstracto; con dataset, se evidencia en métricas.
4. **Planificar fallbacks antes del incidente:** la devolución exige al menos un motor alternativo; Bing/Yandex bajo SerpAPI cumplieron ese rol sin nuevas cuentas.
5. **No confundir “API up” con “RF cumplido”:** health checks y HTTP 200 no garantizan utilidad de negocio.

---

## 7. Estado actual

- Primario: **Google Reverse Image**.
- Respaldo: **Bing + Yandex** (configuración `SEARCH_FALLBACK_ENGINES`).
- Scraping dinámico automático para plataformas JS y baja confianza estática.
- Documentación de alternativas y plan de pruebas disponibles en este directorio `docs/`.
