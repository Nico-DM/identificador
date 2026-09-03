# Dataset de prueba — Identificador de Artistas

## 1. Descripción general

Dataset de regresión ejecutado con el motor `google_reverse_image` sobre URLs públicas definidas en el manifest. Cada caso corre fase estática y, si está disponible, búsqueda profunda.

- **Fecha de ejecución:** 2026-09-03T00:16:15.156429+00:00
- **Backend evaluado:** `http://localhost:8000`
- **Total de imágenes:** 10
- **Ventana de evaluación:** top 10
- **Búsqueda profunda ejecutada:** 4/10
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
| hist-01 | Fotografía histórica | [Migrant Mother (Dorothea Lange, 1936)](https://upload.wikimedia.org/wikipedia/commons/thumb/5/54/Lange-MigrantMother02.jpg/960px-Lange-MigrantMother02.jpg) | Artista: Dorothea Lange; Fecha: 1936; Dominios esperados: wikipedia.org, loc.gov, moma.org | Wikipedia | 2 | 2016-12-09T21:05:38 | [Wikipedia](https://en.wikipedia.org/wiki/Migrant_Mother) | Correcto | Coincidencia en posición 2; búsqueda profunda: sí. La búsqueda terminó con error pero conservó resultados evaluables. |
| hist-02 | Fotografía histórica | [V-J Day in Times Square (Alfred Eisenstaedt, 1945)](https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Kissing_the_War_Goodbye.jpg/960px-Kissing_the_War_Goodbye.jpg) | Artista: Alfred Eisenstaedt; Fecha: 1945; Dominios esperados: wikipedia.org, gettyimages, life.com | — | — | — | — | Incorrecto | La búsqueda no devolvió candidatos |
| trad-01 | Arte tradicional digitalizado | [La Gioconda (Leonardo da Vinci)](https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/960px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg) | Artista: Leonardo da Vinci; Fecha: 1503; Dominios esperados: wikipedia.org, louvre, wikimedia.org | Wikipedia | 1 | 1931-01-01T00:00:00 | [Wikipedia](https://en.wikipedia.org/wiki/File:Mona_Lisa,_by_Leonardo_da_Vinci,_from_C2RMF_retouched.jpg) | Correcto | Coincidencia en posición 1; búsqueda profunda: sí. La búsqueda terminó con error pero conservó resultados evaluables. |
| trad-02 | Arte tradicional digitalizado | [La noche estrellada (Vincent van Gogh, 1889)](https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg) | Artista: Vincent van Gogh; Fecha: 1889; Dominios esperados: wikipedia.org, moma.org, vangoghmuseum | Wikipedia | 1 | 1931-01-01T00:00:00 | [Wikipedia](https://en.wikipedia.org/wiki/File:Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg) | Correcto | Coincidencia en posición 1; búsqueda profunda: sí. La búsqueda terminó con error pero conservó resultados evaluables. |
| meme-01 | Meme | [Success Kid (Laney Griner, 2007)](https://upload.wikimedia.org/wikipedia/en/thumb/f/ff/SuccessKid.jpg/250px-SuccessKid.jpg) | Artista: Laney Griner; Fecha: 2007; Dominios esperados: wikipedia.org, knowyourmeme, reddit.com | — | — | — | — | Incorrecto | La búsqueda no devolvió candidatos |
| meme-02 | Meme | [Doge (Kabosu)](https://upload.wikimedia.org/wikipedia/en/5/5f/Original_Doge_meme.jpg) | Artista: Atsuko Sato; Fecha: 2010; Dominios esperados: wikipedia.org, knowyourmeme, reddit.com | Reddit · r/todayilearned | 2 | 2014-01-20T09:26:52.037000 | [Reddit · r/todayilearned](https://www.reddit.com/r/todayilearned/comments/4est8n/til_doges_real_name_is_kabosu_and_she_was_rescued/) | Correcto | Coincidencia en posición 2; búsqueda profunda: sí. |
| stock-01 | Fotografía de stock | [Gato doméstico (foto de stock, Wikimedia)](https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/960px-Cat03.jpg) | Artista: desconocido; Fecha: —; Dominios esperados: wikipedia.org, commons.wikimedia, pixabay | — | — | — | — | Incorrecto | La búsqueda no devolvió candidatos |
| stock-02 | Fotografía de stock | [Retrato de gaviota (foto de stock, Wikimedia)](https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Gull_portrait_ca_usa.jpg/960px-Gull_portrait_ca_usa.jpg) | Artista: desconocido; Fecha: —; Dominios esperados: wikipedia.org, unsplash, commons.wikimedia | — | — | — | — | Incorrecto | La búsqueda no devolvió candidatos |
| digital-01 | Arte digital | [Color of Friendship (arte digital, Wikimedia)](https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Color_of_Friendship.jpg/960px-Color_of_Friendship.jpg) | Artista: desconocido; Fecha: —; Dominios esperados: wikipedia.org, wikimedia.org, deviantart | — | — | — | — | Incorrecto | La búsqueda no devolvió candidatos |
| digital-02 | Arte digital | [Paisaje en pixel art](https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Landscape_pixel_art.png/960px-Landscape_pixel_art.png) | Artista: desconocido; Fecha: —; Dominios esperados: wikipedia.org, wikimedia.org, opengameart | — | — | — | — | Incorrecto | La búsqueda no devolvió candidatos |

## 4. Métricas finales

| Métrica | Valor |
|---------|-------|
| Precisión (Correcto / total) | **40.0%** (4/10) |
| Casos correctos | 4 |
| Casos incorrectos | 6 |
| Búsqueda profunda ejecutada | 4/10 |
| Imágenes con candidatos | 4 |
| Imágenes sin candidatos | 6 |
| Tiempo promedio de respuesta | 7.02 s |
| Tiempo mínimo / máximo | 2.01 s / 46.1 s |
| Posiciones de acierto | 2, 1, 1, 2 |
| Tasa de error (fallas de API/excepción) | 0.0% |

### Desglose por veredicto

| Veredicto | Cantidad |
|-----------|----------|
| Correcto | 4 |
| Incorrecto | 6 |

### Motivos de evaluación

| Motivo | Cantidad |
|--------|----------|
| Coincide en el top N | 4 |
| Sin resultados | 6 |

### Desglose por categoría

| Categoría | Total | Correctos |
|-----------|-------|-----------|
| Arte digital | 2 | 0 |
| Arte tradicional digitalizado | 2 | 2 |
| Fotografía histórica | 2 | 1 |
| Meme | 2 | 1 |
| Fotografía de stock | 2 | 0 |
