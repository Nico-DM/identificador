# Análisis de alternativas tecnológicas — búsqueda inversa

Comparativa de motores de búsqueda inversa de imágenes evaluados para el núcleo funcional (RF-002…RF-005). No se implementaron todos; se justifica la elección del stack actual.

---

## 1. Resumen de la decisión

| Rol | Motor | Integración |
|-----|--------|-------------|
| **Histórico (1ª entrega)** | Google Lens (`google_lens` vía SerpAPI) | Implementado; **degradado** para coincidencia exacta |
| **Principal actual** | Google Reverse Image (`google_reverse_image` vía SerpAPI) | Motor por defecto |
| **Fallback** | Bing Reverse Image + Yandex Images (SerpAPI) | Activables con `SEARCH_FALLBACK_ENGINES` |
| **Evaluado, no integrado** | TinEye API | Descartado en favor de motores ya cubiertos por SerpAPI |

**Criterio de elección:** unificar facturación y parsing bajo SerpAPI, disponer de un motor Google orientado a coincidencias de imagen (no solo similitud semántica de Lens), y poder sumar Bing/Yandex sin cambiar el contrato interno (`SearchEngine`).

---

## 2. Google Lens (SerpAPI `google_lens`)

| Aspecto | Evaluación |
|---------|------------|
| **Uso en el proyecto** | Motor de la primera entrega (CLI) y del MVP web inicial. |
| **Precisión observada** | Degradada para el objetivo del proyecto: prioriza resultados de “contenido similar” / semánticos frente a copias exactas o fuentes originales. |
| **Limitaciones** | Evolución del producto Google hacia embeddings; la pestaña web “Find image source” no se refleja de forma equivalente en la API Lens. |
| **Términos / acceso** | Vía SerpAPI (cuenta y cuota del plan). Sujeto a ToS de SerpAPI y de Google. |
| **Viabilidad** | Conservado como adaptador (`google_lens`) por compatibilidad, **no recomendado** como primario. |

Detalle del impacto: [contingencia-google-lens.md](contingencia-google-lens.md).

---

## 3. Google Reverse Image (SerpAPI `google_reverse_image`) — elegido como primario

| Aspecto | Evaluación |
|---------|------------|
| **Uso en el proyecto** | `SEARCH_ENGINE=google_reverse_image` (default en código y `render.yaml`). |
| **Precisión observada** | Mejor alineación con coincidencias de imagen y páginas fuente que Lens en las pruebas del proyecto; es el motor usado en el dataset de regresión. |
| **Limitaciones** | Sigue siendo un intermediario (SerpAPI); cobertura y ranking dependen de Google; cuotas y costo por búsqueda. |
| **Términos / acceso** | Misma cuenta SerpAPI; parámetro `image_url`. |
| **Viabilidad** | **Alta** — reemplazo directo del motor degradado sin cambiar frontend ni scoring. |

---

## 4. Bing Reverse Image (SerpAPI `bing_reverse_image`) — fallback implementado

| Aspecto | Evaluación |
|---------|------------|
| **Uso en el proyecto** | Adaptador `BingVisualEngine`; alias `bing_visual`. |
| **Precisión observada** | Complementa al primario cuando éste devuelve pocas URLs; aporta diversidad de hosts. |
| **Limitaciones** | Sin `safe_search` equivalente en el adaptador; calidad variable según consulta; cuota SerpAPI compartida. |
| **Términos / acceso** | SerpAPI (no Azure Bing Visual Search nativo). |
| **Viabilidad** | **Alta** como fallback — mismo patrón Strategy, sin nueva cuenta Azure. |

> Nota: Bing Visual Search “nativo” de Azure fue considerado en la devolución; se priorizó el motor Bing expuesto por SerpAPI para no fragmentar credenciales ni parsers.

---

## 5. Yandex Images (SerpAPI `yandex_images`) — fallback implementado

| Aspecto | Evaluación |
|---------|------------|
| **Uso en el proyecto** | Adaptador `YandexImagesEngine`; tab `similar`. |
| **Precisión observada** | Útil para ampliar candidatos y cubrir fuentes menos visibles en Google/Bing. |
| **Limitaciones** | Resultados y metadatos heterogéneos; parsing defensivo; cuota SerpAPI. |
| **Términos / acceso** | SerpAPI. |
| **Viabilidad** | **Alta** como segundo/tercer motor de fusión (RRF). |

---

## 6. TinEye API — evaluado, no implementado

| Aspecto | Evaluación |
|---------|------------|
| **Precisión** | Reconocido por coincidencia exacta y listados de usos históricos; atractivo para el dominio artístico. |
| **Limitaciones** | Plan free ~50 búsquedas/día; API y modelo de datos distintos a SerpAPI; otra clave y otro adaptador a mantener. |
| **Términos / acceso** | Cuenta TinEye Developer; ToS propios. |
| **Viabilidad para esta PPS** | **Media/baja en el plazo** — el beneficio marginal es menor una vez disponibles Google Reverse Image + Bing + Yandex bajo el mismo proveedor. Queda como mejora futura si se necesita más cobertura de matches exactos. |

---

## 7. Mecanismo de fallback en el código

```
SEARCH_ENGINE=google_reverse_image
SEARCH_FALLBACK_ENGINES=yandex_images,bing_reverse_image
SEARCH_MIN_URLS_BEFORE_FALLBACK=3
```

Si el primario aporta menos URLs que el umbral, se consultan los fallbacks y se fusionan con **Reciprocal Rank Fusion** (`search_engines/fusion.py`), sin que `search_service` ni el frontend conozcan el proveedor concreto.

---

## 8. Conclusión

1. **Abandonar Lens como primario** por degradación semántica documentada.
2. **Adoptar `google_reverse_image`** como reemplazo Google vía SerpAPI.
3. **Implementar Bing + Yandex** como respaldo integrado, no TinEye, para minimizar superficie operativa.
4. **Desacoplar** con interfaz `SearchEngine`.
