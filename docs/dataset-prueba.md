# Dataset de prueba — Identificador de Artistas

## 1. Descripción general

Dataset de regresión ejecutado con el motor `google_reverse_image` sobre URLs públicas definidas en el manifest. Cada caso corre fase estática y, si está disponible, búsqueda profunda.

- **Fecha de ejecución:** 2026-10-15T04:21:08.402096+00:00
- **Backend evaluado:** `http://localhost:8000`
- **Total de imágenes:** 10
- **Ventana de evaluación:** top 10
- **Búsqueda profunda ejecutada:** 9/10
- **Categorías cubiertas:** Fotografía contemporánea, Arte digital, Webcomic, Meme nativo (publicación original)

Archivos relacionados:

- `identificador-api/dataset/manifest.json` — definición de casos y expectativas
- `identificador-api/dataset/results.json` — salida cruda de la última corrida
- `identificador-api/scripts/run_dataset.py` — ejecutor de regresión

## 2. Criterio de evaluación

| Veredicto | Criterio |
|-----------|----------|
| **Correcto** | Al menos un resultado del top 10 (tras búsqueda profunda si aplica) coincide con un dominio esperado. |
| **Incorrecto** | Sin resultados, error de API, o ninguna fuente esperada en el top 10. |

**Precisión** = casos Correctos / total.

## 3. Resultados por imagen

### `photo-01` — Correcto

- **Imagen:** [Success Kid / Why I oughta... (Laney Griner)](https://upload.wikimedia.org/wikipedia/en/f/ff/SuccessKid.jpg)
- **Categoría:** Fotografía contemporánea
- **Esperado:** Artista: Laney Griner; Fecha: 2007-08-31; Dominios esperados: flickr.com/photos/sammyjammy, flickr.com
- **Coincidencia:** Flickr (posición 1)
- **Fecha detectada:** 2007-08-31T00:00:00
- **URL fuente:** [Flickr](https://www.flickr.com/photos/sammyjammy/1285612321)
- **Notas:** Coincidencia en posición 1; búsqueda profunda: sí.

### `photo-02` — Correcto

- **Imagen:** [York Floods 2015 #1 (Richard Scott)](https://commons.wikimedia.org/wiki/Special:FilePath/York_Floods_2015_-1_residential_street.jpg)
- **Categoría:** Fotografía contemporánea
- **Esperado:** Artista: Richard Scott; Fecha: 2015-12-27; Dominios esperados: flickr.com/photos/rjscott, flickr.com
- **Coincidencia:** flickr.com (posición 1)
- **Fecha detectada:** 2026-10-15T00:00:00
- **URL fuente:** [flickr.com](https://www.flickr.com/photos/rjscott/with/19847575443/)
- **Notas:** Límite de lotes alcanzado; se evaluaron los resultados disponibles (10 candidatos, status=batch_done).

### `photo-03` — Incorrecto

- **Imagen:** [Reaching For Light (Alan Levine / cogdogblog)](https://commons.wikimedia.org/wiki/Special:FilePath/2014-365-178_Reaching_For_Light_(14501169726).jpg)
- **Categoría:** Fotografía contemporánea
- **Esperado:** Artista: Alan Levine; Fecha: 2014-06-28; Dominios esperados: flickr.com/photos/cogdog, flickr.com
- **Coincidencia:** — (posición —)
- **Fecha detectada:** 2017-01-03T00:00:00
- **URL fuente:** —
- **Notas:** Límite de lotes alcanzado; se evaluaron los resultados disponibles (10 candidatos, status=batch_done).

### `digital-01` — Correcto

- **Imagen:** [The Watcher (David Revoy)](https://www.davidrevoy.com/data/images/blog/2012/10/2012-10-08_the-watcher_final_by_David_Revoy.jpg)
- **Categoría:** Arte digital
- **Esperado:** Artista: David Revoy; Fecha: 2012-10-08; Dominios esperados: deviantart.com/deevad, davidrevoy.com, deviantart.com
- **Coincidencia:** David Revoy (posición 7)
- **Fecha detectada:** 2015-05-01T00:00:00
- **URL fuente:** [David Revoy](https://www.davidrevoy.com/static9/shop)
- **Notas:** Coincidencia en posición 7; búsqueda profunda: sí.

### `digital-02` — Incorrecto

- **Imagen:** [TMIM Heroine (Bleed)](https://opengameart.org/sites/default/files/sprite0_3.png)
- **Categoría:** Arte digital
- **Esperado:** Artista: Bleed; Fecha: 2014-03-23; Dominios esperados: opengameart.org/content/tmim-heroine, opengameart.org
- **Coincidencia:** — (posición —)
- **Fecha detectada:** 2023-11-07T00:00:00
- **URL fuente:** —
- **Notas:** Sin coincidencia en el top 10 (9 candidatos).

### `digital-03` — Correcto

- **Imagen:** [Aqua Dream (David Revoy)](https://commons.wikimedia.org/wiki/Special:FilePath/Aqua_dream_by_deevad.png)
- **Categoría:** Arte digital
- **Esperado:** Artista: David Revoy; Fecha: 2013-07-23; Dominios esperados: deviantart.com/deevad, davidrevoy.com, deviantart.com
- **Coincidencia:** davidrevoy.com (posición 3)
- **Fecha detectada:** 2013-07-23T00:00:00
- **URL fuente:** [davidrevoy.com](https://www.davidrevoy.com/article177/video-timelapse-aqua-dream)
- **Notas:** Límite de lotes alcanzado; se evaluaron los resultados disponibles (10 candidatos, status=batch_done).

### `digital-04` — Correcto

- **Imagen:** [Pepper first artwork (David Revoy)](https://www.peppercarrot.com/0_sources/0ther/artworks/low-res/2014-06-14_pepper_first-artwork_by-David-Revoy.jpg)
- **Categoría:** Arte digital
- **Esperado:** Artista: David Revoy; Fecha: 2014-06-14; Dominios esperados: peppercarrot.com, davidrevoy.com
- **Coincidencia:** David Revoy (posición 1)
- **Fecha detectada:** 2014-06-14T00:00:00
- **URL fuente:** [David Revoy](https://www.davidrevoy.com/article449/pepper)
- **Notas:** Coincidencia en posición 1; búsqueda profunda: sí.

### `comic-01` — Correcto

- **Imagen:** [Pepper&Carrot Ep.1 p.01 — The Potion of Flight (David Revoy)](https://www.peppercarrot.com/0_sources/ep01_Potion-of-Flight/low-res/en_Pepper-and-Carrot_by-David-Revoy_E01P01.jpg)
- **Categoría:** Webcomic
- **Esperado:** Artista: David Revoy; Fecha: 2014-05-10; Dominios esperados: peppercarrot.com, davidrevoy.com
- **Coincidencia:** Pepper&Carrot (posición 1)
- **Fecha detectada:** 2016-05-05T00:00:00
- **URL fuente:** [Pepper&Carrot](https://www.peppercarrot.com/th/webcomic/ep01_Potion-of-Flight__hd.html)
- **Notas:** Coincidencia en posición 1; búsqueda profunda: sí.

### `meme-01` — Incorrecto

- **Imagen:** [Doge / Kabosu (Atsuko Sato)](https://upload.wikimedia.org/wikipedia/en/5/5f/Original_Doge_meme.jpg)
- **Categoría:** Meme nativo (publicación original)
- **Esperado:** Artista: Atsuko Sato; Fecha: 2010-02-13; Dominios esperados: kabosu112.exblog.jp, kabochan.blog.jp, exblog.jp
- **Coincidencia:** — (posición —)
- **Fecha detectada:** 2016-04-14T19:21:30.102000
- **URL fuente:** —
- **Notas:** Sin coincidencia en el top 10 (8 candidatos).

### `meme-02` — Correcto

- **Imagen:** [Plenkton / Cursed Plankton (Moopintot)](https://i.kym-cdn.com/photos/images/original/002/963/026/31b.jpg)
- **Categoría:** Meme nativo (publicación original)
- **Esperado:** Artista: Moopintot; Fecha: 2010-04-22; Dominios esperados: deviantart.com/moopintot, deviantart.com
- **Coincidencia:** DeviantArt · Moopintot (posición 1)
- **Fecha detectada:** 2010-04-22T00:00:00
- **URL fuente:** [DeviantArt · Moopintot](https://www.deviantart.com/moopintot/art/Plenkton-161635958)
- **Notas:** Coincidencia en posición 1; búsqueda profunda: sí.


## 4. Métricas finales

| Métrica | Valor |
|---------|-------|
| Precisión (Correcto / total) | **70.0%** (7/10) |
| Casos correctos | 7 |
| Casos incorrectos | 3 |
| Búsqueda profunda ejecutada | 9/10 |
| Imágenes con candidatos | 10 |
| Imágenes sin candidatos | 0 |
| Tiempo promedio de respuesta | 31.27 s |
| Tiempo mínimo / máximo | 2.01 s / 78.13 s |
| Posiciones de acierto | 1, 1, 7, 3, 1, 1, 1 |
| Tasa de error (fallas de API/excepción) | 0.0% |

### Desglose por veredicto

| Veredicto | Cantidad |
|-----------|----------|
| Correcto | 7 |
| Incorrecto | 3 |

### Motivos de evaluación

| Motivo | Cantidad |
|--------|----------|
| Límite de lotes con resultados parciales | 3 |
| Fuera del top N | 2 |
| Coincide en el top N | 5 |

### Desglose por categoría

| Categoría | Total | Correctos |
|-----------|-------|-----------|
| Arte digital | 4 | 3 |
| Fotografía contemporánea | 3 | 2 |
| Meme nativo (publicación original) | 2 | 1 |
| Webcomic | 1 | 1 |
