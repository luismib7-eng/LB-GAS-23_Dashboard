# Errores resueltos — LB GAS 23

Fallos que ya ocurrieron en este proyecto, con su causa real. Todos tienen una causa
contraintuitiva: el síntoma apuntaba a otro lado. Revisa este archivo antes de dar por
buena una hipótesis que "suena lógica".

> **Antes de tocar el tablero, lee este archivo completo.** El error 18 ocurrió
> porque no se hizo: una corrección documentada aquí llevaba semanas ausente del
> código publicado y nadie lo verificó. Comprueba además que las funciones
> nombradas en las soluciones existan de verdad en el `index.html` vigente.

---

## 1. Datos sintéticos presentados como reales — **el más caro**

**Qué pasó.** El `fallback.csv` de una compilación temprana traía precios generados al azar
entre $22.50 y $24.50. Con esos datos se redactaron ganchos comerciales con cifras concretas
sobre estaciones de prospectos reales (Hidrosina, Gazpro y otros) y se enviaron correos.

**Cómo se detectó.** Huella estadística de la distribución: 100 decimales distintos y cero
concentración en los valores comerciales típicos (.99, .50, .00). Los precios reales se
amontonan en terminaciones comerciales; los aleatorios no.

**Causa.** Un archivo de respaldo pensado para que el tablero no quedara en blanco se usó
como fuente de verdad.

**Regla que dejó.** Antes de poner una cifra en material que sale hacia un cliente, trázala
hasta un archivo concreto. Si no se puede trazar, no se escribe.

---

## 2. Carpeta anidada en GitHub — rompió el workflow **y** las Pages a la vez

**Síntoma doble.** GitHub Actions fallaba con `exit code 2` y GitHub Pages devolvía 404.
Parecían dos problemas distintos.

**Causa única.** Todos los archivos quedaron dentro de `lbgas23-monitor-nuevo1/` en vez de la
raíz del repositorio. Python no encontraba los scripts y Pages no encontraba `index.html`.

**Cómo evitarlo.** El árbol del commit debe ser plano en la raíz. Ojo adicional: los archivos
que empiezan con punto (`.nojekyll`, `.github/`) **no se suben** al arrastrarlos al navegador.

---

## 3. "Re-run jobs" en lugar de "Run workflow" — ocurrió dos veces

**Síntoma.** Se corregía el código, se volvía a correr y fallaba exactamente igual.

**Causa.** "Re-run jobs" reejecuta **el commit viejo**. El arreglo nunca se ejecutaba.

**Mitigación implementada.** El workflow ahora imprime el SHA del commit y una advertencia
explícita en el paso de verificación. Si el SHA no es el último, el log lo dice.

---

## 4. "Competencia por marca" mostraba solo BP y ARCO NORTE

**Diagnóstico equivocado inicial.** Se pensó que era un filtro mal aplicado.

**Causa real.** La CNE publica razones sociales, no banderas. En su momento solo 37 de 13,770
estaciones traían un nombre de marca dentro de la razón social. **Hoy la columna `Marca` está
vacía en el 100% de los registros.**

**Solución.** Se reemplazó el agrupamiento por marca con detección de **grupo operador** por
razón social: ~630 operadores con 3 o más estaciones a nivel nacional.

> **Corrección del 20 de octubre de 2026.** Esta entrada decía "93 en Jalisco". El padrón da
> **25 operadores con 3 o más estaciones en Jalisco**; 93 era el conteo de los que tienen
> **dos o más** (94 en el corte del 19 de octubre). Ver el archivo de esquemas y cifras.

**Reincidencia.** Se arregló un panel y se dejó el otro. La corrección hay que aplicarla
tanto en `renderCompetencia` como en `renderMarcasChart`. Siguen vivos dos lugares donde el
concepto "marca" puede reaparecer.

---

## 5. Tema claro ilegible en las gráficas

**Causa.** Chart.js reutilizaba las instancias creadas con los colores del tema anterior; las
etiquetas quedaban blancas sobre fondo claro.

**Solución.** Al cambiar de tema se destruyen todas las instancias
(`Object.keys(charts).forEach(k => destroy(k))`) y se reaplican los defaults
(`Chart.defaults.color / borderColor / font.family`) antes de volver a dibujar.

---

## 6. "41,549 estaciones" en pantalla

**Las cifras estaban bien; las etiquetas no.** 41,549 son *registros* (3 cortes × ~13,850).
Las estaciones únicas son 13,854. Las "27,052 estaciones que sostuvieron precio" eran
*comparaciones* entre cortes consecutivos.

**Regla.** Cuando un conteo cruce varios cortes, la palabra es "registros" o "comparaciones".

> **Nota del 20 de octubre de 2026.** La ventana pasó de 3 a 7 cortes (`--conservar 7`), así
> que el factor de inflación de este error es ahora 7, no 3. Ver los errores 15 y 18.

---

## 7. Logotipo 404 en la compilación consolidada

**Causa.** Se incrustó el logo como data URI en el HTML pero `CFG.LOGO_URL` seguía apuntando
al archivo suelto, que ya no se copiaba.

**Regla.** Al consolidar un recurso, hay que cambiar también su referencia en la
configuración, no solo en el marcado.

---

## 8. Ediciones perdidas por una aserción posterior

**Síntoma.** Un cambio aplicado "exitosamente" no aparecía en el archivo.

**Causa.** Varias ediciones en un mismo script, con una verificación intermedia que lanzaba
excepción **antes** de la escritura a disco. Todo lo anterior se perdía.

**Regla.** Cada edición en su propio paso, con su propia escritura.

---

## 9. Llamadas huérfanas tras eliminar código

Al retirar el motor de inferencia de ubicación quedó viva una llamada a `inferirUbicacion`.
También se intentó llamar a `llenarSelectorSim()`, que nunca existió — la función real es
`renderSimulador()`.

**Regla.** Al borrar una función, busca sus llamadas. Al llamar una, confirma que existe.

---

## 10. Dictámenes de terceros con premisas falsas

De un dictamen técnico recibido, **cuatro de sus hallazgos eran falsos** al verificarlos:

| Afirmación del dictamen | Verificación |
|---|---|
| "`reporte_mercado.csv` tiene fecha estancada" | Falso: tiene las 45 fechas |
| "Sigue agrupando por Marca" | Falso: ya se había cambiado a operador |
| "Mapa sin clustering satura el DOM" | Falso: usa modo canvas y tope de 2,500 marcadores |
| "El selector de periodo está desactivado" | Falso: nunca lo estuvo |

Dos sí eran correctos y se implementaron: 85 estaciones en coordenadas (0,0) —se añadió la
caja envolvente de México— y el bloqueo de proyección de utilidad con margen negativo.

**Regla.** Un dictamen externo es una hipótesis, no un hallazgo. Verifica cada punto contra
el código antes de ejecutar, y di cuáles no procedían y por qué.

> **Segunda ocurrencia, 20 de octubre de 2026.** Un dictamen sobre el competidor Signal Fuels
> traía cuatro tareas; **tres partían de premisas falsas**: conservar una columna de estatus
> que no existe en ningún endpoint de la CNE, agregar al buscador campos que ya acepta (y la
> marca, que está vacía al 100%), y quitar una carpeta `v2/` que no existe. Ver el archivo de
> contrainteligencia sobre Signal Fuels.

---

## 11. El tablero descargaba 6.5 MB dos veces en cada primera visita

**Síntoma reportado.** Dos peticiones 404 a `tar_referencia.csv` en la consola. Parecía
cosmético.

**Lo que había debajo.** Al medir contra el log del servidor —no contra la consola—
`fallback.csv`, `catalogo_estaciones.csv` e `historico.csv` llegaban con **dos GET cada uno,
con marcas de tiempo separadas 3.4 segundos**. Unos 6.5 MB duplicados por visita nueva.

**Causa.** El listener de `controllerchange` llamaba a `location.reload()` sin condición. En
la primera visita no existe controlador: el worker se instala, llama a `clients.claim()` y eso
dispara `controllerchange` aunque no haya ninguna versión nueva que aplicar. La página se
recargaba sola. El aviso de actualización sí tenía la guarda correcta
(`navigator.serviceWorker.controller`); la recarga no.

**Solución, y por qué la bandera se arma.** Se recuerda si existía controlador al cargar. La
primera versión del arreglo fue `if (!teniaControlador) return;`, que corrige la primera
visita pero **deja muerto el botón de actualizar en esa misma sesión**: si con la pestaña
abierta se publica una versión y el usuario acepta el aviso, ese segundo `controllerchange`
también se descartaba. La forma correcta consume el primer evento y **arma** la bandera:

```javascript
var teniaControlador = !!navigator.serviceWorker.controller;
var recargando = false;
navigator.serviceWorker.addEventListener("controllerchange", function () {
  if (recargando) return;
  if (!teniaControlador) { teniaControlador = true; return; }  // instalación, no actualización
  recargando = true;
  location.reload();
});
```

**Verificado en navegador, los dos escenarios.** Primera visita: 1 navegación, sin recarga.
Publicar una versión con la pestaña abierta y aceptar el aviso: recarga. Con la variante sin
armar, el segundo escenario devolvía 0 navegaciones —el botón no hacía nada—.

**Dato relacionado.** `TAR_CSV` (Tarifa de Almacenamiento y Reparto) quedó en cadena vacía:
el ETL no genera ese archivo. La guarda `if (CFG.TAR_CSV && CFG.TAR_CSV.trim())` ya existía en
`load()`, así que basta el valor vacío para que el `fetch` no se dispare. Las instancias de
cliente nunca tuvieron el 404 porque `construir_config()` de `preparar_cliente.py` no emite
esa llave.

**Regla.** Un 404 en consola puede ser la punta de un problema de red mucho mayor. Mide contra
el log del servidor, no contra la consola: la consola no distingue una petición de dos.

---

## 12. Auditar el paquete equivocado

**Qué pasó.** Una auditoría externa reportó que dos correcciones "se describieron pero no se
guardaron en el archivo". Al verificar, las dos estaban físicamente en el `index.html`
entregado: la auditoría había abierto el ZIP de la **entrega anterior**.

**Regla.** Antes de concluir que un cambio no se aplicó, confirma el nombre y la fecha del
paquete que estás abriendo. Y al entregar, nombra la versión de forma que no se confunda con
la anterior.

**Nota aparte.** En ese mismo dictamen el señalamiento del archivo era falso, pero el patrón
de código propuesto **sí era mejor** que el implementado (ver error 11). Las dos cosas pueden
ser ciertas a la vez: la premisa equivocada no invalida automáticamente la sugerencia.

---

## 13. El ZIP de entrega borró diez días de serie acumulada

**Qué pasó.** Al subir el paquete de optimizaciones al repositorio, `historico.csv`,
`reporte_mercado.csv` y `movimientos.csv` quedaron sobrescritos con la foto que traía el ZIP
—el corte del 2 de octubre—. Las corridas diarias habían estado acumulando correctamente del
3 al 12.

**Diagnóstico equivocado inicial.** Se atribuyó el hueco a una falla del workflow. La pestaña
Actions lo desmintió: todas las corridas en verde, incluidas las del 8, 9, 10 y 11 de octubre.
El workflow nunca falló.

**Causa.** Esos tres archivos **se acumulan**: el ETL lee lo que ya existe y le suma el día.
Un paquete que los lleve congelados los regresa al pasado. Como Luis reemplaza todos los
archivos de golpe —que es su preferencia declarada y es correcta para el código—, el efecto
fue inmediato.

**Recuperación.** Se restauraron desde copias previas y desde el historial de commits de
GitHub, verificando con hashes SHA-1 por fecha que las fechas solapadas fueran idénticas antes
de fusionar. `historico.csv` y `reporte_mercado.csv` quedaron completos (56 fechas).
`movimientos.csv` quedó en 8 fechas: el 3, 4, 5 y 6 de octubre no existen en ningún respaldo
porque el repositorio tampoco corrió esos días —la firma son las 1,899 filas del 7 de octubre,
el triple de un día normal, que es lo que produce una comparación que salta varios días—.

**Regla permanente.** Los ZIP de entrega **no incluyen** `historico.csv`, `movimientos.csv`
ni `reporte_mercado.csv`. Sí incluyen el código (`index.html`, `sw.js`, los `.py`, el workflow)
y los datos que el ETL regenera completos en cada corrida (`fallback.csv`,
`catalogo_estaciones.csv`, `historico.xlsx`).

**Dato de arquitectura que conviene no confundir.** El selector de PERIODO del tablero se
construye desde `fallback.csv`, que es ventana móvil de 7 cortes del padrón completo. La
gráfica de tendencia se construye desde `historico.csv`, que guarda promedios por ámbito.
Restaurar el histórico no agrega periodos al selector; son fuentes distintas.

> **Ampliación del 20 de octubre de 2026 (ver error 18).** Este mismo mecanismo aplica al
> CÓDIGO, no solo a los datos: una entrega completa que reemplaza `index.html` puede
> regresar el archivo a un estado anterior y borrar una corrección ya hecha. Así se perdió
> el arreglo del error 15.

---

## 14. El chip de referencia atribuía a Profeco un promedio que no era de Profeco

**Qué pasó.** El chip del riel de dispersión decía "Promedio nacional Profeco" durante toda la
sesión, mientras el marcador del riel se posicionaba con el promedio real del histórico. Dos
cosas mal a la vez: una atribución falsa —la clasificación del tablero es por percentiles
locales, no la metodología de márgenes de Profeco— y un valor capturado a mano ($23.68) que
nadie actualizaba.

**Diagnóstico equivocado inicial.** Al leer el código parecía un caso de respaldo raro:
`benchVigente()` prefiere el último corte de `historico.csv` y solo cae a `CFG.BENCHMARK` si el
histórico no cargó.

**Causa real.** El texto del chip se escribía **una sola vez, en `init()`**, cuando el histórico
todavía no había cargado. En ese instante `benchVigente()` sí devolvía el respaldo. Las dos
líneas de `renderRail()` que tocaban el chip solo alternaban `hidden`, nunca reescribían la
etiqueta. No era un borde: era lo que veía cada visitante, siempre.

**Solución.** La etiqueta se escribe en `renderRail()` con el dato del corte cargado.
`CFG.BENCHMARK` quedó con los tres productos en `null` y la etiqueta neutra: si el histórico no
carga, el riel no pinta referencia en lugar de mostrar un número viejo.

**Regla.** Una cadena que se fija en `init()` describe el estado vacío, no el estado con datos.
Si el texto depende de datos cargados, se escribe en el render.

**Crédito donde toca.** Lo encontró un dictamen externo (Grok). De sus siete hallazgos, dos eran
reales; este es el más valioso que ha producido cualquiera de los cuatro dictámenes externos
recibidos. Un dictamen con cinco puntos falsos puede traer uno que importe.

---

## 15. "Todos los periodos" contaba registros como estaciones en cuatro paneles

> **ESTA CORRECCIÓN SE PERDIÓ DEL CÓDIGO Y EL FALLO VOLVIÓ. Ver error 18.**

**Qué pasó.** `computeMercado()` construía la rejilla espacial desde `periodRows()`. Con el
selector de PERIODO en "Todos los periodos", `periodRows()` devuelve los 7 cortes de
`fallback.csv`, así que la rejilla indexaba cada estación una vez por corte. Consecuencias en
cadena: `vecinos()` devolvía al mismo competidor repetido, `referenciaLocal()` promediaba
duplicados, `universoLocal()` rendía 70 observaciones para un municipio de 10 estaciones, la
clasificación por percentiles contaba renglones, y `descargarVecindario()` exportaba con la
columna de corte vacía. El KPI decía "41,330 estaciones con precio".

**Es el error 6 otra vez, en paneles que no se corrigieron entonces.** En 2026 se arregló el
conteo de la cabecera y se dejó vivo el mismo fallo en el riel, la competencia, el comparativo y
el KPI.

**Alcance real del daño: ninguno.** Se revisaron los CSV de vecindario que ya se habían usado
para material comercial —Palma Real, Becktrop, Polanco y los demás—: todos traen un solo corte y
permisos únicos, porque siempre hubo una fecha seleccionada. Ninguna propuesta enviada llevó
cifras infladas. El fallo estaba a un clic de distancia, no realizado. **Verificar el alcance
antes de declararlo importa tanto como encontrar el fallo:** decirle al titular que sus
propuestas llevaban cifras malas habría sido falso.

**Solución.** La capa de referencia de mercado se construye siempre sobre un corte
(`corteMercado()` / `filasCorteMercado()`): rejilla, promedios por ámbito, vecindario,
clasificación, briefing y selectores de estación. La tabla y los KPI sí pueden abarcar varios
cortes, porque ahí el usuario lo pide; lo que cambió es que ahora lo declaran. Una sola función
—`unidadFilas()`— decide la palabra para los cinco paneles que cuentan filas, y
`panoramaCorte()` quedó como alias de `corteMercado()` para que no haya dos definiciones de
"cuál es el corte vigente".

**Regla.** Cuando un fallo de etiquetado aparece en un panel, busca los demás paneles que
cuentan lo mismo y resuélvelo con una sola función compartida. Dos definiciones del mismo
concepto es la forma en que este error regresa.

---

## 16. `preparar_cliente.py` no podía volver a correr sobre una carpeta de cliente

**Qué pasó.** Al propagar código nuevo a las dos instancias de cliente preservando su
configuración, los dos `index.html` quedaron con el bloque `<script id="app">` **duplicado** y la
página rota.

**Causa.** El bloque `window.APP_CONFIG` se localizaba buscando el literal `};`. El logotipo
viaja dentro de la configuración como data URI, y las instancias generadas con versiones
anteriores del generador cerraron el objeto con `}` sin punto y coma —válido en JavaScript por
inserción automática—. La búsqueda se saltaba ese cierre y se enganchaba al siguiente `};` del
archivo: el de `var CFG = window.APP_CONFIG || {};`, ya dentro del script de la aplicación. El
corte se llevaba el final de la configuración y el encabezado del script.

**Lo encontré rompiendo los archivos con ese mismo método.** `preparar_cliente.py` tenía —y
tiene su origen en— exactamente la misma línea: `html.find("};", ini)`. Funcionaba porque solo
se ejecutaba contra el `index.html` raíz, cuya configuración sí cierra con `};`.

**Solución.** `limites_app_config()` delimita el bloque **contando llaves**, ignorando cadenas y
comentarios de bloque, y acepta el cierre con o sin punto y coma. Probada contra tres casos: el
index raíz (bloque de 131 KB con data URI), una instancia de cliente (1.6 KB, cierre sin punto y
coma) y un caso con `}` dentro de una cadena.

**Recuperación.** Los dos `index.html` se reconstruyeron desde el raíz reinyectando su
configuración rescatada por conteo de llaves, verificando que quedara un solo
`<script id="app">`, un solo `window.APP_CONFIG`, sintaxis válida en los dos bloques y la
configuración idéntica byte a byte.

**Regla.** No delimites un bloque de código por un literal de dos caracteres cuando el contenido
puede incluirlo. Y si un script solo se ha probado contra su archivo de origen, no asumas que
funciona contra su propia salida.

---

## 17. El README describía una arquitectura que ya no existía

**Qué pasó.** El README documentaba `app.js`, `styles.css` y `config.js` como archivos
separados, ingesta por Google Sheets, automatización con Apps Script, "competencia directa por
marca" y un motor de inferencia de ubicación con un diccionario `MUNICIPIOS`. Nada de eso existe:
la aplicación es un `index.html` consolidado, la ingesta es por XML de la CNE con GitHub Actions,
la agrupación es por grupo operador y el motor de inferencia se retiró (ver error 9).

**Costo real.** Dos auditorías externas leyeron ese README y reportaron como defectos cosas
inexistentes. Una documentación desactualizada no es deuda cosmética: es una fuente de
diagnósticos equivocados que cuestan tiempo verificar.

**Regla.** Si un commit cambia la arquitectura, actualiza el README en el mismo commit. El
README reescrito lleva una nota al inicio que dice qué describía la versión anterior, para que
quien haya leído la vieja sepa que cambió.

---

## 18. La corrección del error 15 se perdió del código, y nadie lo notó en semanas

**Qué pasó.** El 20 de octubre de 2026, con una campaña de publicidad a punto de
pagarse, una revisión del sitio publicado encontró que **el error 15 estaba
otra vez en pantalla**. Con el selector de PERIODO en "Todos los periodos", el
panel de competidores directos marcaba **266 competidores donde hay 38** —35
más baratos donde hay 5, 224 al mismo precio donde hay 32—, el riel decía
"96,458 estaciones con precio" y la tabla "96,971 estaciones listadas".

**No se reintrodujo: se había perdido.** Al auditar el `index.html` publicado,
las funciones con las que se resolvió el error 15 —`corteMercado()`,
`filasCorteMercado()`, `unidadFilas()`— **no existen en el archivo**. Solo
sobrevivió `panoramaCorte()`. La corrección estaba documentada en este mismo
registro y ausente del código.

**Causa.** Es el mecanismo del error 13 aplicado al código en vez de a los
datos: una entrega completa que reemplaza `index.html` regresa el archivo a un
estado anterior. Como la preferencia declarada —correcta— es reemplazar todos
los archivos de golpe, una sola entrega construida sobre una línea sin el
arreglo lo borra en silencio. No hay prueba automatizada que lo detecte y el
síntoma solo aparece con una opción del selector que no es la de omisión.

**Agravante, y es responsabilidad de quien construyó las versiones 14 a 21.**
Esas versiones se construyeron sobre la línea sin la corrección y nadie leyó
este archivo antes de tocar el tablero, que es exactamente lo que las
instrucciones del proyecto piden al terminar un cambio. Peor: en la v17 se
corrigió **este mismo fallo** en el panel de grupo operador —que contaba
registros y los rotulaba estaciones— y no se buscaron los demás paneles que
contaban lo mismo. La regla del error 15 lo decía con todas sus letras.

**Alcance del daño.** El fallo estaba en el sitio público, a un clic de
distancia: bastaba elegir "Todos los periodos". No se detectó ningún material
comercial afectado, porque los recortes de vecindario usados en propuestas
siempre llevaron una fecha seleccionada. Lo que sí estaba en riesgo era la
campaña: un anuncio que lleva a un director al tablero y le muestra 266
competidores donde hay 38 destruye la credibilidad que el anuncio acaba de
comprar.

**Solución (v21), y en qué se aparta de la original.** Una sola función,
`unicas(filas)`, colapsa a una fila por estación conservando el corte más
reciente —el precio vigente—. Se aplica en dos puntos, no en quince:

1. `construirRejilla()` indexa estaciones únicas. Eso corrige de un golpe
   `vecinos()`, `vecindario()` y `referenciaLocal()`, que es la cadena que
   producía los 266.
2. `render()` separa explícitamente los dos conjuntos:

```javascript
var rows = scoped();      // REGISTROS: los 7 cortes
var est  = unicas(rows);  // una fila por ESTACIÓN
```

`est` va a los doce paneles que cuentan estaciones. **`renderProfeco(rows)`
sigue recibiendo el conjunto completo a propósito**: la vista de dinámica mide
el movimiento ENTRE cortes y sin ellos no tendría qué medir.

A diferencia del arreglo original, la tabla ahora muestra **estaciones únicas
con su precio vigente** en vez de declarar que abarca varios cortes. 13,858
estaciones reales son más útiles que 96,969 renglones repetidos, y así la
palabra "estaciones" es cierta en lugar de necesitar una aclaración.

**Verificado en los dos modos.** Un corte: 13,854 estaciones, 70 competidores
en el radio. Todos los periodos: 13,858 estaciones, **70 competidores** —antes
490—. La diferencia de 4 estaciones es correcta: a lo largo de 7 cortes
algunas reportan unos días y otros no, así que la unión es mayor que cualquier
corte individual. La dinámica sigue viendo sus 7 cortes y 6 días medidos.

**Reglas que deja.**

1. **Antes de tocar el tablero, lee este archivo.** La v17 corrigió medio
   fallo porque no se leyó.
2. **Un arreglo documentado aquí pero ausente del código es un arreglo
   perdido.** Al retomar el proyecto, verifica que las funciones nombradas en
   las soluciones de este registro existan en el `index.html` publicado. Es
   una búsqueda de treinta segundos y habría ahorrado semanas de regresión.
3. **Cuando un fallo de conteo aparece en un panel, corrígelo con una función
   compartida y revisa TODOS los paneles que cuentan lo mismo** en el mismo
   cambio. Es la regla del error 15, que ya estaba escrita y aun así falló
   por no aplicarse.
