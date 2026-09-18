---
name: data-visualization
description: Crea gráficas claras y verificables desde datos heterogéneos.
version: 0.1.0
author: Amo (zorrovengador), Pandora/Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [data, visualization, charts, dashboards, design, accessibility]
    related_skills: []
---

# Data Visualization Skill

Convierte datos entregados en CSV, XLSX, JSON, tablas Markdown, texto o estructuras Python en gráficas y dashboards legibles, sobrios y visualmente distintivos. Prioriza exactitud, jerarquía visual, trazabilidad y accesibilidad; el glassmorphism es una capa de presentación, nunca un pretexto para ocultar datos o reducir contraste.

## Cuándo usarla

Usa esta skill cuando el usuario pida:

- una gráfica para explicar tendencias, comparaciones, composición, distribución o relaciones;
- un dashboard, reporte visual o exportación PNG, SVG, HTML o PDF;
- transformar una tabla o archivo de datos en una visualización ejecutiva;
- mejorar una gráfica existente sin alterar sus cifras.

No la uses para inferir causalidad, pronosticar o corregir datos sin autorización. Si el usuario pide una recomendación de negocio, separa hechos observados, cálculos, hipótesis y decisión.

## Prerrequisitos

- Identifica el formato de entrada y conserva una copia inmutable del original.
- Usa `read_file` para archivos de texto y `search_files` para localizar insumos; usa `terminal` para ejecutar scripts reproducibles.
- Para XLSX, utiliza la skill `xlsx` o una biblioteca ya disponible; no instales paquetes globalmente.
- Comprueba las dependencias disponibles antes de ejecutar: Python estándar siempre es la base; pandas, matplotlib, seaborn, plotly, openpyxl, kaleido o weasyprint son opcionales.
- Si falta una dependencia, reporta el bloqueo y propone un entorno virtual; no inventes que la gráfica fue renderizada.

## Contrato de entrada

Antes de graficar, registra:

1. Fuente, formato, periodo, unidad y granularidad.
2. Variables disponibles y sus tipos: temporal, categórica, numérica, porcentaje, moneda o identificador.
3. Filtros, agregaciones y transformaciones aplicadas.
4. Valores faltantes, duplicados, outliers y cambios de escala.
5. Pregunta que la gráfica debe responder y audiencia prevista.

Conserva nombres, acentos, unidades y valores originales. Nunca conviertas silenciosamente pesos a dólares, porcentajes a proporciones ni fechas ambiguas a otra zona horaria.

## Selección de gráfica

Elige la forma más simple que responda la pregunta:

- Tendencia temporal: línea, área sólo cuando el total acumulado importa.
- Comparación de categorías: barras horizontales ordenadas; evita pastel salvo pocas partes de un total claro.
- Composición: barras apiladas o 100% apiladas; etiqueta el denominador.
- Distribución: histograma, densidad o boxplot; muestra tamaño de muestra.
- Relación: dispersión con escala y unidades; no dibujes una línea causal por defecto.
- Geografía: mapa sólo si la dimensión espacial cambia la decisión.
- KPI: número destacado con periodo, unidad, delta y denominador.

No uses 3D, dobles ejes o escalas truncadas salvo que exista una razón explícita y quede señalada en el subtítulo. Ordena categorías de modo que la comparación sea inmediata.

## Sistema visual

Aplica un sistema consistente, no una colección de adornos:

- Fondo base oscuro o claro neutro; superficies tipo vidrio con opacidad moderada, borde tenue y sombra suave.
- Una familia tipográfica sans-serif disponible localmente; máximo dos pesos y tres tamaños funcionales.
- Paleta semántica: un color de énfasis, neutros para contexto y colores de estado sólo con significado definido.
- No dependas sólo del color: combina color con posición, forma, textura o etiquetas.
- Rejilla mínima, ejes ligeros y etiquetas directas cuando reduzcan el esfuerzo de lectura.
- Márgenes seguros y ritmo consistente; evita cortar títulos, leyendas o etiquetas.
- El diseño debe sobrevivir en escala de grises, en pantalla pequeña y al exportar a PDF.

El glassmorphism debe ser sutil: si el fondo, la transparencia o el brillo compiten con los datos, redúcelo. Una gráfica bonita que nadie puede leer es sólo decoración con autoestima.

## Procedimiento

1. **Inspeccionar.** Lee el insumo, cuenta filas y columnas, detecta tipos y registra metadatos. Criterio: el esquema y las anomalías quedan documentados.
2. **Validar.** Comprueba rangos, duplicados, faltantes, unidades, fechas y denominadores. Criterio: cada transformación tiene una justificación escrita.
3. **Definir la pregunta.** Escribe un título que responda qué, dónde y cuándo; añade subtítulo con unidad, filtro y fuente. Criterio: una persona puede entender el mensaje sin abrir el archivo original.
4. **Elegir la geometría.** Selecciona un tipo de gráfica de la tabla anterior. Criterio: la geometría no introduce una comparación que los datos no soporten.
5. **Construir.** Genera primero una versión técnicamente simple y después aplica el sistema visual. Criterio: la versión decorada conserva exactamente posiciones, valores y escalas.
6. **Etiquetar.** Usa formato numérico consistente, separadores locales, unidad visible y precisión suficiente. Criterio: las cifras importantes se pueden leer sin adivinar.
7. **Exportar.** Produce, cuando sea útil, un formato editable/interactivo y uno estático: HTML o SVG para inspección, PNG a resolución suficiente y PDF sólo si se verificó su render. Criterio: cada archivo abre y conserva texto, leyenda y dimensiones.
8. **Revisar visualmente.** Usa `vision_analyze` sobre el artefacto renderizado o inspecciona capturas frescas. Verifica clipping, contraste, solapamientos, leyendas, escalas, densidad y jerarquía. Criterio: no queda ningún defecto material.
9. **Reconciliar.** Recalcula totales, extremos, promedios y deltas desde la fuente y compáralos con lo mostrado. Criterio: las cifras visibles coinciden o las diferencias están explicadas.
10. **Entregar.** Incluye archivos, fuente, fecha de generación, filtros, transformaciones, limitaciones y una lectura breve. Criterio: otra persona puede reproducir la gráfica y distinguir observación de interpretación.

## Reglas para datos faltantes y outliers

- No rellenes faltantes sin marcar el método y su impacto.
- Distingue cero, vacío, no aplica y no reportado.
- No elimines outliers por estética; márcalos, usa escala apropiada o documenta la exclusión autorizada.
- Si una categoría tiene pocos registros, muestra `n` y evita conclusiones fuertes.
- Para porcentajes, muestra siempre el denominador o el tamaño de muestra cuando sea relevante.

## Salidas recomendadas

Entrega una carpeta con nombres descriptivos y estables:

- `chart.svg` o `chart.html`: evidencia editable/interactiva.
- `chart.png`: vista estática para compartir.
- `data_dictionary.md`: columnas, unidades y reglas.
- `README.md`: fuente, filtros, transformaciones, comando ejecutado y limitaciones.
- `qa/RECEIPT.md`: evidencia visual, reconciliación y estado final.

No publiques credenciales, datos personales innecesarios, archivos temporales ni copias de fuentes sensibles.

## Verificación

La entrega sólo puede declararse `APPROVED` cuando:

- el archivo existe y se puede abrir;
- la gráfica fue inspeccionada desde una salida fresca, no sólo desde el código;
- títulos, unidades, fechas, leyendas y acentos son correctos;
- no hay clipping, solapamiento, contraste insuficiente ni etiquetas ilegibles;
- las cifras principales reconcilian con la fuente;
- el diseño funciona sin color como única señal;
- se documentaron filtros, transformaciones, faltantes, outliers y limitaciones.

Si falla algo material, usa `REVISION_REQUIRED` o `BLOCKED`; nunca presentes una salida no renderizada como terminada.

## Errores frecuentes

- Embellecer antes de validar: produce errores muy atractivos.
- Usar pastel para series largas o valores parecidos.
- Ocultar el cero, truncar ejes o mezclar unidades sin advertencia.
- Usar una paleta de moda sin semántica ni contraste.
- Presentar una correlación como causalidad.
- Confundir un dashboard interactivo con una auditoría de datos.
- Declarar que un PDF o PNG funciona sin abrir el archivo resultante.
- Inventar tendencias cuando el periodo, denominador o tamaño de muestra no están disponibles.
