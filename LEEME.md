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
