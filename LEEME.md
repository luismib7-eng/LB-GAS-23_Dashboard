# v15 · Unificado: seguridad/legal + corrección de dinámica

**Dos archivos: `index.html` y `sw.js`. Reemplazan los de la raíz del repo.**
Ningún CSV se toca. `historico.csv` y `movimientos.csv` quedan intactos.

Service worker: `lbgas23-v9` → **`lbgas23-v10`**. Recarga dos veces al publicar.

Este paquete **sustituye a los dos ZIP anteriores**
(`LBGAS23_fix_dinamica_2026-10-19` y `lbgas23-v14-seguridad-legal`).
No cargues ninguno de los dos por separado: cada uno tiene solo la mitad.

---

## Cómo se unificó, y por qué se puede afirmar que no hay conflicto

Los dos ZIP salieron de la **misma base** del repositorio. Se reconstruyó esa
base revirtiendo el parche de dinámica, y se aislaron los dos conjuntos de
cambios por separado. Los rangos que toca cada uno:

| Parche | Líneas de la base que modifica |
|---|---|
| Seguridad y legal | 2, 1566, 1911, 2062, 2134, 6830 |
| Dinámica | 4718 – 4902 |

**No se tocan.** Ambos se aplicaron sobre la base y el resultado es
**byte por byte idéntico en los dos órdenes de aplicación**, que es la prueba
de que ninguno pisa al otro. No se copió y pegó nada a mano.

---

## Contenido 1 · Corrección de `calcularDinamica()`

La ventana conserva los últimos cortes **cargados**, no los últimos días. Un par
que abarca un hueco medía el acumulado del hueco y lo presentaba como si fuera
un día: inflaba la movilidad y sesgaba el reparto alzas/bajas.

`patronCompetencia()` ya resolvía esto con `diasEntreCortes(a,b) !== 1`. El
criterio se propagó al otro bloque; no se inventó nada nuevo.

Además, ahora **se declara en pantalla** cuántos días se midieron de verdad y
cuántos pares se descartaron. Verificado con el padrón real de 5 cortes que
incluye el salto del 2 al 13 de octubre:

> **Movimientos por estación** · 5 cortes del padrón · **3 días medidos** ·
> **1 par descartado por hueco entre cortes**

La gráfica dibuja 3 barras, no 4. Las tarjetas dicen *"13,792 estaciones
seguidas en 3 transición(es) **de un día**"*.

El estado vacío también cambió: antes decía que faltaban cortes; ahora explica
que no hay dos cortes **consecutivos**, que es la condición real.

---

## Contenido 2 · Seguridad y cumplimiento legal

### Lo que ya estaba bien y NO se tocó

Se auditó antes de escribir. Seis directrices ya estaban cumplidas:

| Directriz | Estado real |
|---|---|
| Escapado en inyecciones al DOM | 0 de 37 `innerHTML` interpolan variables sin escapar; `esc()` existe y se usa |
| `eval`, `document.write`, `new Function` | Cero ocurrencias |
| Inyección por parámetros de URL | No se leen: cero `location.search`, cero `URLSearchParams` |
| `chart.destroy()` antes de redibujar | Las 6 gráficas pasan por el helper `destroy(name)` |
| `clearLayers()` en el mapa | Ya presente |
| `console.log` de desarrollo | Cero en el código propio |

### Y una que no aplica

El tablero **no usa geolocalización**: cero `navigator.geolocation`, cero
`map.locate()` en código propio. Las distancias salen de las coordenadas del
catálogo de la CNE. Declarar "cálculo de distancias por geolocalización en
tiempo real" habría sido confesar en el aviso un tratamiento de datos que no
ocurre. El aviso dice lo contrario: **que la ubicación no se solicita.**

### Lo que se agregó

**Política de Seguridad de Contenido** (`<meta http-equiv>`), cerrada a los
cuatro orígenes que el tablero usa de verdad:

```
default-src 'self'; script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' data: https://fonts.gstatic.com;
img-src 'self' data: blob: https://*.tile.openstreetmap.org;
connect-src 'self'; manifest-src 'self'; worker-src 'self';
object-src 'none'; base-uri 'self'; form-action 'none';
frame-ancestors 'none'; upgrade-insecure-requests
```

**Dos límites que debes conocer.** `'unsafe-inline'` es inevitable: toda la
aplicación va embebida para que abra como archivo estático. Lo que sí se cierra
—y es lo que importa— son los orígenes externos de salida. Y **`frame-ancestors`
no surte efecto por meta**: solo como cabecera HTTP, y GitHub Pages no las
permite. El navegador lo reporta en consola; es esperado, no un error. Queda
declarado para cuando migres de alojamiento.

**Service worker: coincidencia de host anclada.** La regla de mosaicos era
`/tile\.openstreetmap\.org/` sin anclar, que **también casa con
`tile.openstreetmap.org.dominio-ajeno.com`**: bastaba registrar ese nombre para
que el service worker cacheara contenido ajeno como si fuera del mapa. Ahora es
igualdad exacta o sufijo `.tile.openstreetmap.org`.

**Aviso de Privacidad (LFPDPPP)** en modal desde el pie, con el patrón existente
(`data-close`, cierre con Escape): responsable, sitio estático sin servidor ni
formularios, no se solicita ubicación, no se tratan datos sensibles, qué guarda
el almacenamiento local y cómo borrarlo, y derechos ARCO a `lbgas23@gmail.com`.

Lleva además un apartado que la directriz no pedía: **los dos terceros que
reciben la IP del visitante por el solo hecho de cargar la página** —Google
Fonts y los mosaicos de OpenStreetMap—. Una plantilla genérica lo omite; un
comprador corporativo que audite el sitio lo detecta en treinta segundos.

**Consentimiento de almacenamiento local:** banner flotante con "Entendido" y
acceso al aviso. La bandera va en `localStorage` **entre `try/catch`**. Si no se
puede leer el consentimiento, el banner se muestra: fallar hacia mostrarlo
molesta una vez más, pero nunca omite el aviso a quien no lo ha visto. El
bloque de JavaScript es autocontenido, fuera del IIFE principal.

**Deslinde legal** en el pie y dentro del simulador. El del simulador es más
directo porque es donde se decide:

> *Escenario matemático, no asesoría financiera. Sin tu costo por litro esto es
> diferencial contra el mercado, no utilidad. El resultado no garantiza
> rendimientos: depende de variables que esta plataforma no observa, empezando
> por tu volumen real.*

---

## Verificado sobre el archivo unificado, no sobre las partes

Los 7 bloques de JavaScript pasan `node --check`. Servido local con el padrón
real y abierto en Chromium:

```
ERRORES JS                : ninguno
AVISOS CSP                : solo el esperado de frame-ancestors
banner visible al entrar  : sí
#consentOk oculta banner  : sí
sigue oculto al recargar  : sí
modal abre del pie y del banner, cierra con Escape
declara NO geolocalizar   : sí
declara Google Fonts y OSM: sí
ARCO a lbgas23@gmail.com  : sí
dinámica                  : 5 cortes · 3 días medidos · 1 par descartado
```

**Nota de la prueba:** aparece un 404 de `denue.csv` porque mi carpeta de prueba
no lo incluye. No es un fallo: el código lo resuelve con
`.then(buildDenueSafe, function(){ return null; })` y el tablero sigue
mostrando la razón social. En tu repositorio el archivo sí existe.

---

## Pendiente, y no depende del código

- **`frame-ancestors` real:** requiere cabecera HTTP. Motivo para mover el
  alojamiento si un cliente lo exige en auditoría, no para tocar el tablero.
- **Píxel de Meta y medio de contacto:** falta tu Pixel ID.

---
---

# v16 · Se agrega la corrección del ETL (19 oct, tarde)

Este paquete ya **no es solo el tablero**. Trae dos archivos más, porque al
recalcular las cifras de la base de conocimiento apareció un defecto que estaba
programado para destruir datos.

## El defecto: el histórico sí se estaba recortando

La regla 1.2 del proyecto dice que `historico.csv` no se borra, recorta ni
reformatea. **El flujo diario lo estaba recortando.**

`.github/workflows/actualizar-datos.yml` corría con
`--historico-conservar 120`, y `escribir_historico()` en `xml_a_csv.py` hacía
exactamente lo que ese número pide:

```python
if conservar and len(fechas) > conservar:
    vigentes = set(fechas[-conservar:])
    todas = [f for f in todas if ... in vigentes]
```

La serie arranca el **19 de agosto de 2026** y hoy lleva 62 fechas sin un solo
hueco. En la fecha 121 el corte automático empieza a tirar la más antigua:

> **El 17 de diciembre de 2026 se habría borrado el 19 de agosto**, y de ahí una
> fecha por día.

El pacto SENER vence en **febrero de 2027**. El recorte habría destruido el
"antes" de la comparación antes/después **dos meses antes de que llegara el
"después"** — el único activo del producto que no se puede comprar más tarde,
porque la CNE no republica series.

`movimientos.csv` tenía lo mismo con `--movimientos-conservar 400`: primer
borrado el 9 de noviembre de 2027.

## La corrección, en tres capas

1. **Workflow:** los dos topes a `0`. `--conservar 7` del padrón **no se toca**:
   ése sí es una ventana móvil a propósito.
2. **Valores por omisión:** `120 → 0` y `400 → 0`, para que una corrida sin la
   bandera tampoco recorte.
3. **Blindaje en el código:** se agregó `_conservar_sin_borrar()`. Si alguien
   vuelve a pasar un número, **no borra nada**: avisa por `stderr` nombrando las
   fechas que se habrían perdido. El parámetro queda solo como alarma de tamaño.

La tercera capa es la que importa: las dos primeras se revierten con un
descuido de una línea.

## Probado contra el archivo real, no sobre el papel

Se cargaron las dos versiones del ETL en el mismo proceso y se corrieron contra
el `historico.csv` real de 62 fechas, con las 13,854 filas reales del corte del
19 de octubre:

```
VIEJO  con --historico-conservar 10 ->  10 fechas (2026-10-11 -> 2026-10-20)  BORRO 53
NUEVO  con --historico-conservar 10 ->  63 fechas (2026-08-19 -> 2026-10-20)  conservo todo

sin tope (0), viejo vs nuevo identicos byte a byte: True
```

La última línea es la que da tranquilidad: **sin tope, el parche no cambia
absolutamente nada** del comportamiento normal. Solo quita el borrado.

## Qué reemplazar

| Archivo | Dónde va |
|---|---|
| `index.html` | raíz del repo |
| `sw.js` | raíz del repo |
| `xml_a_csv.py` | raíz del repo |
| `actualizar-datos.yml` | `.github/workflows/` |

Los CSV **no se tocan**. El próximo corte ya no recorta.

## Un horizonte que sí queda abierto

`movimientos.csv` crece ~84 KB por fecha (~30 MB al año) y **GitHub rechaza
archivos de más de 100 MB**: son unos **3.3 años**. No lo carga el navegador, así
que no afecta la apertura del tablero, pero cuando se acerque la salida es
**archivar por año**, no recortar. Queda anotado en la base de conocimiento.

---
---

# v17 · "Estaciones" que eran registros, en dos paneles

Lo detectó Luis mirando la tarjeta de un grupo operador y preguntando si ese
número eran sus estaciones o los registros del precio. Eran registros.

## Qué estaba mal

`renderCompetencia()` acumulaba un valor por **fila** del padrón:

```js
(porGrupo[razon] = porGrupo[razon] || []).push(r[p]);
...
n: fuente[k].length          // <- registros, rotulados "estaciones"
```

La ventana conserva **7 cortes**, así que el mismo permiso aparece siete veces.
Un operador de 546 estaciones aportaba 3,822 registros, y la tarjeta decía
"3,822 estaciones".

| Grupo | Decía | Estaciones reales |
|---|---|---|
| Servicios Gasolineros de México | 3,822 | **546** |
| Petromax | 1,939 | **277** |
| Servicio Fácil del Sureste | 770 | **110** |
| Energía y Servicios Coordinados | 665 | **95** |
| Mega Gasolineras | 637 | **91** |
| Combu-Express | 539 | **77** |
| E.S.G.E.S | 427 | **61** |
| Grupo Octano | 392 | **56** |

**Y había un segundo efecto, peor que el número inflado.** El filtro
`fuente[k].length >= minimo` también contaba registros, así que un operador de
**una sola estación** entraba a una lista titulada "grupos con dos o más
estaciones" con solo haber reportado dos días. El universo del subtítulo pasaba
de **1,422 grupos reales a 8,222**.

El mismo defecto estaba en `renderMarcasChart()` — la gráfica de "operadores con
tres o más estaciones" de la vista Profundidad.

**Por qué nadie lo vio antes:** con el selector de Periodo en una fecha concreta,
registros y estaciones coinciden y el panel es correcto. Solo se desvía en
"Todos los periodos". Y empeoró en silencio cuando el flujo pasó de 3 a 7
cortes: el error se multiplicó de ×3 a ×7.

## La corrección

Un helper compartido, `acumularGrupo()`, que separa las dos cosas que nunca
debieron ir juntas:

- `precios` → un valor por registro, para promediar sobre el periodo
- `sitiosN` → permisos **distintos**, que es el conteo de estaciones

La llave es `permitKey()`, que ya existía y normaliza los dos formatos que
conviven en el padrón (`PL/…` y `CNE/PL/…`). El promedio no cambia: sigue
calculándose sobre todos los registros del periodo, que es lo correcto y lo que
lo hace comparable con el promedio de referencia.

El tooltip ahora **declara las dos cifras**, para que no se vuelva a confundir:

> 110 estaciones en la selección · promedio $23.69 **sobre 770 registros** ·
> −0.00 contra el promedio de la zona

## Verificado contra el padrón, no contra sí mismo

Los conteos se calcularon aparte en Python sobre `fallback.csv` y se comparó
contra lo que pinta el navegador con "Todos los periodos":

```
subtitulo: 8 de 1422 en la seleccion   (antes: 8 de 8222)
  SERVICIO FACIL DEL SURESTE      110 estaciones · -0.00 vs. zona
  MEGA GASOLINERAS                 91 estaciones · +0.27 vs. zona
  PETROMAX                        277 estaciones · +0.28 vs. zona
  SERVICIOS GASOLINEROS DE MEXICO 546 estaciones · +0.32 vs. zona
  E.S.G.E.S                        61 estaciones · +0.34 vs. zona
  COMBU-EXPRESS                    77 estaciones · +0.38 vs. zona
  GRUPO OCTANO                     56 estaciones · +0.48 vs. zona
  ENERGIA Y SERVICIOS COORDINADOS  95 estaciones · +0.50 vs. zona
```

Los ocho coinciden con el cálculo independiente. **Los precios y los
diferenciales no se movieron ni un centavo**: el parche solo toca el conteo.

---
---

# v18 · Panel de cumplimiento del tope

Viene de un ejercicio de contrainteligencia sobre **Signal Fuels
(Cassiopeia)**, un competidor nuevo y distinto de fuelpricing. El dictamen que
llegó traía cuatro tareas; **tres partían de premisas falsas** y se
verificaron contra el código antes de tocar nada:

| Pedía | Realidad verificada |
|---|---|
| Conservar la columna de estatus del padrón | **No existe** en ningún endpoint de la CNE. Y lo pedía en `preparar_cliente.py`, que no construye el catálogo |
| Que el buscador acepte permiso, municipio y marca | **Ya lo hace**, menos marca — que está vacía en el 100% de los registros |
| Quitar la carpeta envolvente `v2/` | **No existe.** La raíz solo tiene `clientes/` |

En su lugar se construyó lo que sí sale de la evidencia.

## El panel

El 19 de octubre, Expansión publicó un análisis de PetroIntelligence: *"86.5%
comercializaba diésel a un máximo de 27 pesos"*, o sea 13.5% de
incumplimiento. Tu padrón da **exactamente 13.5% por encima de $27.00** — el
mismo número, calculado solo.

Pero el compromiso es **menor a** $27.00, no "a un máximo de". Con esa
distinción:

| Diésel, corte del 19 oct | |
|---|---|
| Cumple (por debajo de $27.00) | 42.3% — 4,448 |
| **Exactamente en $27.00** | **44.2% — 4,652** |
| Por encima | 13.5% — 1,415 |

**El incumplimiento real es 57.7%, no 13.5%.** En Regular: 82.4% / 5.0% /
12.6% → 17.6% real.

El tablero ya clasificaba bien por estación: `excedeTope` usa `precio >= tope`,
que es lo correcto. Lo que faltaba era el agregado.

## Lo que hace

Tres tarjetas —cumple, exactamente en el tope, por encima— que se recalculan
con el filtro activo. Verde, ámbar y rojo, en ese orden, porque el grupo de en
medio es el que cree que cumple y no cumple.

- **Comparación en centavos enteros** (`Math.round(v*100)`). Con flotantes, un
  $27.00 publicado puede llegar como 26.999999 y caer del lado equivocado.
- **Premium degrada solo**: no está en el pacto, y el panel lo dice en vez de
  mostrar un cero que se lea como dato.
- El pie declara que es un **pacto voluntario, no una norma sancionable**, y
  que la Zona Libre de la Frontera Norte produce precios legítimamente
  menores.

Verificado en navegador contra el padrón real: los tres porcentajes de los dos
productos reproducen un cálculo independiente en Python, dígito por dígito.

## Sobre los precios TAD

Signal Fuels vende "precios TAD actualizados cada día". Lo investigué porque
si fueran públicos y diarios habría una brecha real:

- El conjunto por terminal de datos.gob.mx dice **"actualización a febrero de
  2026"**. Ocho meses de retraso.
- El portal público de Pemex entrega un **PDF**, con "última actualización:
  mayo 2026".
- Y ese precio se publica **"antes de impuestos y fletes"**, textual.

**No pude verificar un precio TAD diario y por terminal en ninguna fuente
pública.** Y aunque existiera, no es el costo del gasolinero: le faltan flete
y descuento de contrato. Es la regla 1.4, confirmada por la fuente oficial.
`tar_referencia.PLANTILLA.csv` ya resuelve lo que ellos no.

---
---

# v19 · Quién marca el precio en tu radio

**Archivos: `index.html`, `sw.js`, `xml_a_csv.py`, `preparar_cliente.py`,
`actualizar-datos.yml` y `conducta.csv`.** El último es un archivo de datos
nuevo; va a la raíz como los demás CSV y se regenera en cada corte.

Service worker sigue en **`lbgas23-v10`**.

## Por qué esto y no los indicadores macro

Es lo único que ningún competidor puede construir. No sale de ninguna fuente
pública: sale de `movimientos.csv`, que existe porque tú lo acumulas desde el
1 de octubre. La CNE no republica series, así que **nadie puede reconstruir
hacia atrás lo que no guardó.** Ni Signal Fuels a $2,699 al mes, ni
fuelpricing a $4,930.

## El archivo derivado, y por qué no se carga la bitácora directa

`movimientos.csv` pesa 1.26 MB y crece ~84 KB al día: en un año son 30 MB que
el navegador bajaría en cada carga. Eso rompe la ligereza de la PWA, que es
justo lo que te distingue.

El ETL ahora escribe **`conducta.csv`**: una fila por estación **que se ha
movido** —4,016 hoy, no 14,944— con 177 KB. **No crece con los días**, crece
con las estaciones que participan. El navegador lo carga a prueba de fallos:
si no está, el panel se oculta y el resto del tablero funciona igual.

## Qué mide, y qué NO

El padrón se publica una vez al día. **No se puede saber quién movió primero
dentro del mismo día, y el tablero no lo afirma.** Lo que sí se separa es el
episodio:

- **Inicia** — movió un día válido sin que ningún vecino de su radio se
  hubiera movido en los dos días previos.
- **Sigue** — movió cuando alguien del radio ya se había movido.

Excluyentes, y suman los días evaluados.

### Una métrica que descarté a medio camino

La primera versión contaba *lidera* como "algún vecino movió después". Se
saturaba: en un radio con 100 vecinos siempre hay alguien moviéndose, así que
las primeras filas salían `Lidera 9 / Sigue 10` — toda estación líder y
seguidora a la vez. No medía nada. La definición por episodio sí discrimina:
de 511 estaciones con 3 o más movimientos evaluados, **42 siempre inician y
238 siempre siguen**.

### Dos días que el cálculo tira, y por qué

1. **Los que siguen a un hueco.** El 7 de octubre marcó 1,521 estaciones
   porque faltaban del 3 al 6: son cambios acumulados, no sincronización.
   Mismo criterio que `patronCompetencia()` y `calcularDinamica()`.
2. **Los de movimiento masivo**, por encima de 3 veces la mediana. El 13 de
   octubre marcó 2,682 contra una mediana de 503. Eso es recuperación de
   datos o un cambio fiscal nacional, no conducta local.

Sin esas dos exclusiones, el tablero leería **recuperación de datos como
sincronización de precios**. El resumen del ETL declara cuántos días usó.

## Lo que sale hoy

Nacional, corte del 19 de octubre: **29.7% inicia, 70.3% reacciona.** En
México el precio al público se mueve por reacción, no por iniciativa. Es un
hecho de mercado que nadie está publicando.

**Jalisco inicia más que el país: 35.4%.** Ese contraste se recalcula solo con
cualquier filtro.

Y la rigidez: **71% de las estaciones no ha movido precio desde el 1 de
octubre**; las que sí, llevan una mediana de 6 días sin moverse. El que no
mueve no está compitiendo por precio, y eso cambia a quién vigilas.

## La reserva honesta

La bitácora lleva 15 fechas y perdió cuatro días del 3 al 6 de octubre. La
señal es real —la verifiqué antes de construir— pero todavía es delgada, y
**se vuelve más firme cada día que pasa.** Eso está escrito en el pie del
panel; no se presenta como conclusión cerrada.

## Correcciones de cableado que encontré al integrar

- **`git add` del workflow no incluía `conducta.csv`.** Se habría generado en
  cada corrida y nunca se habría publicado. Corregido junto con `git diff`.
- **`preparar_cliente.py` no copiaba `denue.csv` ni `conducta.csv`** a las
  instancias de cliente: cada inquilino se habría quedado sin nombre comercial
  y sin panel de conducta. Agregados a `DATOS`.

## Para generarlo sin esperar el corte

```bash
python3 xml_a_csv.py precios_del_dia.xml … \
        --movimientos movimientos.csv --movimientos-conservar 0 \
        --conducta conducta.csv --conducta-radio 5
```

El `conducta.csv` que va en este ZIP está calculado contra tu repositorio al
corte del **19 de octubre de 2026**, para que el panel funcione desde que
subas los archivos. El corte diario lo reemplaza.

---
---

# v20 · Índice de tamaño y dispersión del radio

Incluye todo lo de v19. Service worker sigue en **`lbgas23-v10`**.

## 1. Índice de tamaño, del personal ocupado del DENUE

Responde la pregunta que un dueño hace de verdad: **¿el de enfrente es de mi
tamaño o me saca tres veces?**

`denue.csv` ya estaba integrado pero el tablero **tiraba la columna
`Personal`**: solo usaba nombre comercial, dirección y CP. Esa columna tiene
cobertura del **100%** en los registros cruzados y es la mejor aproximación
pública que existe a la escala de una estación.

Ahora aparece como una insignia discreta junto a cada competidor —`11–30`,
`6–10`, `31–50`— y como una lectura en el panel:

> Por **índice de tamaño** —personal ocupado reportado al DENUE del INEGI, no
> volumen de venta— tu estación está en la banda **11–30**. De los **58**
> competidores del radio con cruce en el DENUE, **2** son de una banda mayor y
> **10** de una menor.

### La regla que no se negocia aquí

**Jamás se expresa en litros, y la metodología va a la vista en cada tooltip.**
El padrón de la CNE publica precios, no despacho. El día que el tablero
muestre litros que el cliente no capturó, pierde lo único que lo distingue de
fuelpricing y de Signal Fuels, que es que todo se puede comprobar contra la
fuente. Por eso el texto dice "ordena por escala, no mide venta" en pantalla,
no en una nota al pie.

**Detalle de implementación:** la banda se lee tomando el primer número del
texto, no comparando la cadena completa. El DENUE viene en latin-1 y la
redacción de los rangos cambia entre entregas —"251 y más" contra "251 y
mas"—, así que una comparación literal se rompería en silencio.

## 2. Dispersión del radio (P25–P90)

Un KPI nuevo que contesta **¿hay recorrido o esta plaza ya convergió?**

Se usan P25 y P90, los mismos percentiles con los que el tablero ya clasifica,
**no el mínimo y el máximo**: un solo precio atípico no debe describir la
plaza entera.

Y la lectura declara dónde caes tú, que es un hecho medible y no un juicio:

> Entre el percentil 25 y el 90 del radio hay **$0.01** de diferencia ($23.98
> a $23.99), y tu precio queda por encima del **28%** de la plaza.

Ese ejemplo es real, de una estación de Guadalajara: **43 de sus 70
competidores publican exactamente el mismo precio.** Una dispersión de un
centavo dice, en un vistazo, que mover precio ahí se nota de inmediato. Eso no
se ve en un promedio.

## Verificado

Cero errores de JavaScript, cero 404. Los chips, los dos párrafos de lectura y
el KPI se rindieron contra el padrón real del 19 de octubre y se revisaron en
pantalla. El tooltip de cada insignia declara la fuente y la advertencia de
que no es volumen.
