# Dataset de prueba — Identificador de Artistas

## 1. Descripción general

Dataset de regresión ejecutado con el motor `unknown` sobre URLs públicas definidas en el manifest. Cada caso corre fase estática y, si está disponible, búsqueda profunda.

- **Fecha de ejecución:** 2026-09-08T23:30:57.678651+00:00
- **Backend evaluado:** `http://localhost:8000`
- **Total de imágenes:** 10
- **Ventana de evaluación:** top 10
- **Búsqueda profunda ejecutada:** 10/10
- **Categorías cubiertas:** Fotografía histórica, Arte tradicional digitalizado, Meme, Fotografía de stock, Arte digital

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

| ID | Categoría | Imagen | Resultado esperado | Coincidencia | Posición | Fecha detectada | URL fuente | Veredicto | Observaciones |
|----|-----------|--------|--------------------|--------------|----------|-----------------|------------|-----------|---------------|
| hist-01 | Fotografía histórica | [Migrant Mother (Dorothea Lange, 1936)](https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Lange-MigrantMother02.jpg/960px-Lange-MigrantMother02.jpg) | Artista: Dorothea Lange; Fecha: 1936; Dominios esperados: wikipedia.org, loc.gov, moma.org | Wikipedia | 1 | 2004-09-18T03:48:43 | [Wikipedia](https://en.wikipedia.org/wiki/Florence_Owens_Thompson) | Correcto | Coincidencia en posición 1; búsqueda profunda: sí. |
| hist-02 | Fotografía histórica | [V-J Day in Times Square (Alfred Eisenstaedt, 1945)](https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Kissing_the_War_Goodbye.jpg/960px-Kissing_the_War_Goodbye.jpg) | Artista: Alfred Eisenstaedt; Fecha: 1945; Dominios esperados: wikipedia.org, gettyimages, life.com | en.wikipedia.org | 1 | 2010-06-13T15:49:47 | [en.wikipedia.org](https://en.wikipedia.org/wiki/Unconditional_Surrender_(sculpture)) | Correcto | Coincidencia en posición 1; búsqueda profunda: sí. |
| trad-01 | Arte tradicional digitalizado | [La Gioconda (Leonardo da Vinci)](https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/960px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg) | Artista: Leonardo da Vinci; Fecha: 1503; Dominios esperados: wikipedia.org, louvre, wikimedia.org | Wikipedia | 1 | 2002-08-12T19:21:41 | [Wikipedia](https://en.wikipedia.org/wiki/Mona_Lisa) | Correcto | Coincidencia en posición 1; búsqueda profunda: sí. |
| trad-02 | Arte tradicional digitalizado | [La noche estrellada (Vincent van Gogh, 1889)](https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg) | Artista: Vincent van Gogh; Fecha: 1889; Dominios esperados: wikipedia.org, moma.org, vangoghmuseum | — | — | 2019-12-18T17:58:36 | — | Incorrecto | Sin coincidencia en el top 10 (30 candidatos). |
| meme-01 | Meme | [Success Kid (Laney Griner, 2007)](https://upload.wikimedia.org/wikipedia/en/thumb/f/ff/SuccessKid.jpg/250px-SuccessKid.jpg) | Artista: Laney Griner; Fecha: 2007; Dominios esperados: wikipedia.org, knowyourmeme, reddit.com | — | — | 2012-10-08T07:10:43 | — | Incorrecto | Sin coincidencia en el top 10 (30 candidatos). |
| meme-02 | Meme | [Doge (Kabosu)](https://upload.wikimedia.org/wikipedia/en/5/5f/Original_Doge_meme.jpg) | Artista: Atsuko Sato; Fecha: 2010; Dominios esperados: wikipedia.org, knowyourmeme, reddit.com | — | — | 2025-11-28T06:49:32 | — | Incorrecto | Sin coincidencia en el top 10 (30 candidatos). |
| stock-01 | Fotografía de stock | [Gato doméstico (foto de stock, Wikimedia)](https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/960px-Cat03.jpg) | Artista: desconocido; Fecha: —; Dominios esperados: wikipedia.org, commons.wikimedia, pixabay | — | — | 2018-07-19T09:34:54 | — | Incorrecto | Sin coincidencia en el top 10 (30 candidatos). |
| stock-02 | Fotografía de stock | [Retrato de gaviota (foto de stock, Wikimedia)](https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Gull_portrait_ca_usa.jpg/960px-Gull_portrait_ca_usa.jpg) | Artista: desconocido; Fecha: —; Dominios esperados: wikipedia.org, unsplash, commons.wikimedia | en.wikipedia.org | 1 | 2006-09-29T00:00:00 | [en.wikipedia.org](https://en.wikipedia.org/wiki/Wikipedia:Featured_picture_candidates/October-2006) | Correcto | Coincidencia en posición 1; búsqueda profunda: sí. |
| digital-01 | Arte digital | [Color of Friendship (arte digital, Wikimedia)](https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Color_of_Friendship.jpg/960px-Color_of_Friendship.jpg) | Artista: desconocido; Fecha: —; Dominios esperados: wikipedia.org, wikimedia.org, deviantart | ru.wikipedia.org | 1 | 2026-03-04T00:00:00 | [ru.wikipedia.org](https://ru.wikipedia.org/wiki/%D0%A4%D0%B0%D0%B9%D0%BB:Color_of_Friendship.jpg) | Correcto | Coincidencia en posición 1; búsqueda profunda: sí. |
| digital-02 | Arte digital | [Paisaje en pixel art](https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Landscape_pixel_art.png/960px-Landscape_pixel_art.png) | Artista: desconocido; Fecha: —; Dominios esperados: wikipedia.org, wikimedia.org, opengameart | — | — | 2021-11-18T00:00:00 | — | Incorrecto | Sin coincidencia en el top 10 (30 candidatos). |

## 4. Métricas finales

| Métrica | Valor |
|---------|-------|
| Precisión (Correcto / total) | **50.0%** (5/10) |
| Casos correctos | 5 |
| Casos incorrectos | 5 |
| Búsqueda profunda ejecutada | 10/10 |
| Imágenes con candidatos | 10 |
| Imágenes sin candidatos | 0 |
| Tiempo promedio de respuesta | 79.42 s |
| Tiempo mínimo / máximo | 24.11 s / 114.25 s |
| Posiciones de acierto | 1, 1, 1, 1, 1 |
| Tasa de error (fallas de API/excepción) | 0.0% |

### Desglose por veredicto

| Veredicto | Cantidad |
|-----------|----------|
| Correcto | 5 |
| Incorrecto | 5 |

### Motivos de evaluación

| Motivo | Cantidad |
|--------|----------|
| Fuera del top N | 5 |
| Coincide en el top N | 5 |

### Desglose por categoría

| Categoría | Total | Correctos |
|-----------|-------|-----------|
| Arte digital | 2 | 1 |
| Arte tradicional digitalizado | 2 | 1 |
| Fotografía histórica | 2 | 2 |
| Meme | 2 | 0 |
| Fotografía de stock | 2 | 1 |
