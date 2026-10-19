# Esquemas de datos y cifras verificadas — LB GAS 23

Archivo ligero para la base de conocimiento. Sustituye a cargar los CSV completos
(que hoy suman más de 15 MB de filas repetitivas).

**Verificado el 19 de octubre de 2026** contra el repositorio clonado ese día
(último commit: `Precios 2026-10-19`, 19:32 UTC). Cada cifra de este archivo se
calculó contra el archivo que se cita; ninguna se estimó.

Si una cifra de aquí no cuadra con lo que ves en el tablero, el tablero tiene
razón y este archivo está vencido: regenera la sección antes de usar los números
en material comercial.

---

## 0. Qué cambió respecto de la versión del 6 de octubre

La versión anterior quedó vencida en nueve puntos. Siete son por el paso del
tiempo; **dos eran errores** que podían costar credibilidad en una junta.

| Dato | Decía (6 oct) | Real (19 oct) | Motivo |
|---|---|---|---|
| `fallback.csv` | 41,549 filas · 3 cortes | **96,969 filas · 7 cortes** | El flujo pasó a `--conservar 7` |
| Rango de Regular | $15.94 – $28.89 | **$15.94 – $29.95** (ventana) | Mercado |
| `historico.csv` | 5,535 filas · 45 fechas | **7,626 filas · 62 fechas** | Acumulación diaria |
| `movimientos.csv` | 948 filas | **12,005 filas · 15 fechas** | Acumulación |
| `reporte_mercado.csv` | 1,485 filas · sin percentiles | **2,046 filas · con P25/Mediana/P75/P90** | Ya se regeneró |
| Bloque `marca` | ARCO NORTE + BP | **+ TOTALENERGIES** (2 filas en 62 fechas) | Sigue siendo residuo |
| `denue.csv` | no documentado | **10,671 filas, 77.0% de cobertura** | Archivo nuevo |
| `tar_referencia.PLANTILLA.csv` | no documentado | **plantilla de costo del cliente** | Archivo nuevo |
| **Operadores 3+ en Jalisco** | **93** | **25** | **Error: 93 era el conteo de 2 o más** |

**El error de los 93.** Jalisco tiene 94 operadores con **dos o más** estaciones
en el corte (99 en el catálogo) y solo **25 con tres o más**. La cifra vieja
mezclaba los dos umbrales. Si la dices en una mesa de colegas y alguien la
revisa, pierdes autoridad por un dato que sí se podía calcular.

**Y una corrección regulatoria que no es de estos archivos:** los controles
volumétricos del SAT ya no son el **Anexo 30** sino el **Anexo 21** desde la RMF
2026 (el 31 pasó a ser el 22). Solo cambió la numeración, pero decir "Anexo 30"
frente al contador de un cliente es un error gratuito.

---

## 1. `fallback.csv` — precios publicados

Ventana móvil de los **últimos 7 cortes diarios** (`--conservar 7` en el
workflow). **96,969 filas · 10.33 MB**

```
Fecha,Region,Estado,Municipio,Marca,Estacion,Permiso CRE,Direccion,Regular,Premium,Diesel
```

Cortes en la ventana al 19 de octubre, **todos consecutivos**:

| Corte | Filas | | Corte | Filas |
|---|---|---|---|---|
| 2026-10-13 | 13,850 | | 2026-10-17 | 13,854 |
| 2026-10-14 | 13,851 | | 2026-10-18 | 13,857 |
| 2026-10-15 | 13,852 | | 2026-10-19 | 13,854 |
| 2026-10-16 | 13,851 | | | |

Notas sobre el esquema real:

- `Marca` viene **vacía en el 100% de las filas**: 0 de 96,969. No es muestreo.
- `Direccion` viene vacía en las 96,969. La ubicación utilizable son las
  coordenadas del catálogo; la dirección de calle la aporta el DENUE.
- Las celdas de producto vacías significan "la estación no reporta ese
  producto", **no** cero.
- `Estacion` es la **razón social**, no un nombre comercial.

### Rangos y promedios, corte del 19 de octubre

| Producto | Estaciones | Mínimo | Máximo | Promedio |
|---|---|---|---|---|
| Regular | 13,780 | $15.94 | $29.39 | **$23.6957** |
| Premium | 12,994 | $17.44 | $31.99 | **$28.5972** |
| Diésel | 10,515 | $16.88 | $30.99 | **$26.9945** |

En la ventana completa de 7 cortes el máximo de Regular llega a **$29.95**.

> **El promedio de diésel es $26.9945 contra un tope de $27.00.** Eso no es un
> mercado encontrando su precio: es precio administrado contra el techo del
> pacto. Es el dato más fuerte que tienes para una mesa de colegas.

---

## 2. `catalogo_estaciones.csv` — identidad y geografía

**15,034 filas · 1.55 MB · 15,034 `Place ID` únicos**

```
Permiso CRE,Place ID,Marca,Estacion,Direccion,Municipio,Estado,Region,Lat,Lon
```

- **`Place ID` es la llave de cruce con el archivo de precios.** No el permiso
  CRE (regla 1.3).
- Conviven los dos formatos de permiso: **421 con `CNE/PL/…`** y **14,613 con
  `PL/…`**.
- `Marca` también vacía en las 15,034 filas.
- Registros del corte sin equivalencia en el catálogo: **5 de 13,854 = 0.04%**
  (prefijo `PLACE/`, p. ej. `PLACE/31107`).

---

## 3. `historico.csv` — memoria larga (NUNCA se borra)

**7,626 filas · 0.34 MB · 19 ago 2026 → 19 oct 2026 · 62 fechas · sin un solo hueco**

```
Fecha,Ambito,Clave,Producto,Promedio,Estaciones
```

- Ámbitos: `nacional` (186 filas), `region` (1,488), `estado` (5,952).
- **Son promedios agregados, no precios por estación.** El comportamiento de una
  estación concreta en el tiempo está en `movimientos.csv`.
- Producto se escribe sin acento: `Diesel`, `Premium`, `Regular`.
- Crecimiento: **≈5.5 KB por fecha**. Un año son ~2 MB. No hay razón de tamaño
  para recortarlo.

> **Defecto corregido el 19 de octubre de 2026.** El flujo diario corría con
> `--historico-conservar 120` y `escribir_historico()` **sí recortaba**: se
> quedaba con las últimas 120 fechas y descartaba el resto. Con la serie
> arrancando el 19 de agosto, **el 17 de diciembre de 2026 el corte automático
> habría borrado el 19 de agosto**, y de ahí en adelante una fecha por día.
>
> El pacto SENER vence en febrero de 2027. El recorte habría destruido el
> "antes" de la comparación antes/después justo dos meses antes de que llegara
> el "después" — es decir, el único activo del producto que no se puede comprar
> después, porque la CNE no republica series.
>
> Ya está corregido: el tope pasó a 0 en el workflow y en el valor por omisión,
> y la función se blindó para que **un número distinto de cero nunca borre**;
> avisa por `stderr` y conserva todo.

---

## 4. `movimientos.csv` — comportamiento por estación

Solo registra **cambios** de precio.
**12,005 filas · 1.26 MB · 1 oct 2026 → 19 oct 2026 · 15 fechas**

```
Fecha,Permiso CRE,Estacion,Estado,Municipio,Producto,Anterior,Nuevo,Cambio
```

> **Hueco irrecuperable: faltan el 3, 4, 5 y 6 de octubre de 2026.** El
> comportamiento por estación de esos cuatro días no existe y no se puede
> reconstruir. El histórico de promedios sí está completo.

- Crecimiento: **≈84 KB por fecha** (~800 cambios diarios). Un año son ~30 MB.
- **No lo carga el navegador**: es bitácora de servidor. Su tamaño solo pesa en
  el repositorio, no en el tiempo de apertura del tablero.
- Mismo defecto y misma corrección que el histórico: corría con
  `--movimientos-conservar 400` (primer borrado el 9 de noviembre de 2027). Hoy
  en 0.
- **Horizonte real que sí hay que vigilar:** GitHub rechaza archivos de más de
  100 MB. A 84 KB por día son unos **3.3 años**. Es una fecha lejana pero cierta;
  cuando se acerque, la salida es archivar por año, no recortar.

---

## 5. `reporte_mercado.csv` — reporte comparativo estilo Profeco

**2,046 filas · 0.24 MB · 62 fechas**

```
Fecha,Producto,Bloque,Clave,Estaciones,Promedio,Minimo,Maximo,Diferencial_vs_minimo,
P25,Mediana,P75,P90,Estacion_extremo,Permiso_extremo
```

Los percentiles **ya están** en el archivo del repositorio (la versión anterior
de este documento decía que faltaban).

Bloques: `nacional` (186 filas), `region` (1,488), `marca` (372).

> **Advertencia sobre el bloque `marca`.** Al 19 de octubre detecta
> **ARCO NORTE (1 estación) y BP (36)** — 37 de 15,034 = **0.25% del padrón**.
> Apareció además `TOTALENERGIES`, en 2 filas de 62 fechas. Es residuo de cuando
> el catálogo traía marcas. **No sirve para análisis competitivo.** Conviene
> retirarlo o sustituirlo por un bloque `operador` agrupado por razón social.

---

## 6. `denue.csv` — enriquecimiento del INEGI (SCIAN 468411)

**10,671 filas · 1.46 MB.** Cruza con **10,667 estaciones del corte = 77.0%**
de las 13,854.

```
Permiso CRE,Nombre comercial,Direccion,CP,Personal,Metros
```

| Columna | Cobertura |
|---|---|
| Permiso CRE | 100.0% |
| Nombre comercial | 99.2% |
| Direccion | 100.0% |
| CP | 99.9% |
| Personal | 100.0% |
| Metros | 100.0% |

**No trae columnas de contacto** — verificado; por eso es seguro en un
repositorio público.

Aporta las dos cosas que el padrón de precios no tiene: el **nombre comercial**
—el que se reconoce en la calle, frente a una razón social que muchas veces es
una persona física— y la **dirección de calle**. Si el archivo no existe, el
tablero funciona exactamente como antes.

### Personal ocupado: la base del índice de tamaño

| Banda | Estaciones | Peso |
|---|---|---|
| 11 a 30 personas | 6,801 | 63.7% |
| 6 a 10 personas | 2,408 | 22.6% |
| 31 a 50 personas | 672 | 6.3% |
| 0 a 5 personas | 641 | 6.0% |
| 51 a 100 personas | 137 | 1.3% |
| 101 a 250 personas | 10 | 0.1% |
| 251 y más personas | 2 | 0.0% |

> **Se presenta como índice de tamaño o escala relativa, con metodología visible
> y fuente citada. Jamás como una cifra en litros.** El volumen por estación no
> es público: la CNE declaró confidencial la estructura de costos que pidió en
> agosto de 2026 y el volumen real va al SAT por el Anexo 21.

---

## 7. `tar_referencia.PLANTILLA.csv` — costo del cliente

```
Estado,Producto,Precio_TAR,Vigencia
```

Plantilla **sin un solo precio real**: los tres renglones son el formato.

- `Precio_TAR` = **costo puesto en estación**: terminal + flete − descuentos, con
  impuestos de factura.
- `Vigencia` = `AAAA-MM-DD`. En el tablero `TAR_VIGENCIA_DIAS` está en **30**:
  pasados 30 días se **bloquea la proyección de utilidad** en vez de calcular con
  un costo viejo.
- En la instancia matriz `CFG.TAR_CSV` está **vacío**; cada cliente carga el
  suyo. Verificado en `index.html`.

Es la implementación de la regla 1.4: sin costo por litro no hay margen, hay
diferencial, y se declara en pantalla.

---

## 8. Agrupación por operador (razón social)

**La `Marca` no existe. El eje de análisis competitivo es la razón social.**
Corte del 19 de octubre de 2026:

| Ámbito | Estaciones | Operadores distintos | Con 3 o más | Con 2 o más |
|---|---|---|---|---|
| Nacional (corte) | 13,854 | 8,277 | **633** | — |
| Nacional (catálogo) | 15,034 | 9,053 | **687** | — |
| Jalisco (corte) | 982 | 723 | **25** | **94** |
| Jalisco (catálogo) | 1,060 | 784 | **27** | **99** |

Los 633 operadores nacionales con 3 o más estaciones cubren **5,409 estaciones =
39.0% del corte**. El resto del padrón es de operadores con una o dos.

**Mayores operadores nacionales:** Servicios Gasolineros de México (546),
Petromax (277), Servicio Fácil del Sureste (110), Energía y Servicios
Coordinados (96), Mega Gasolineras (91).

**Mayores en Jalisco (catálogo):** Servicios Gasolineros de México (49),
Combu-Express (37), Petromax (19), Grupo Octano (17), Inmobiliaria Samich (10).

---

## 9. El pacto SENER contra el padrón real

Corte del 19 de octubre. El compromiso es **menor a** el tope, no "hasta": un
precio exactamente en el tope **no cumple**.

| | Estaciones | Sobre el tope | **Exactamente en el tope** | Cumple (< tope) |
|---|---|---|---|---|
| Regular (< $24.00) | 13,780 | 1,732 (12.6%) | 695 (5.0%) | 11,353 (**82.4%**) |
| Diésel (< $27.00) | 10,515 | 1,415 (13.5%) | **4,652 (44.2%)** | 4,448 (**42.3%**) |

> **El 44.2% del mercado de diésel publica exactamente $27.00 y cree que
> cumple.** Sumado al 13.5% que está por encima, **el 57.7% del diésel nacional
> no cumple el compromiso**. Es un pacto voluntario: el riesgo es reputacional y
> comercial, no una multa. Pero es la conversación que nadie en el gremio está
> teniendo con el número en la mano.

---

## 10. Cifras para material comercial

| Dato | Valor verificado | Archivo |
|---|---|---|
| Estaciones en el catálogo CNE | 15,034 | `catalogo_estaciones.csv` |
| Estaciones que reportan precio en un corte | 13,854 | `fallback.csv` (19 oct) |
| Cortes en la ventana móvil | 7 | `--conservar 7` |
| Operadores con 3 o más estaciones (nacional) | 633 | `fallback.csv` |
| Operadores con 3 o más estaciones (Jalisco) | **25** | `fallback.csv` |
| Operadores con 2 o más estaciones (Jalisco) | 94 | `fallback.csv` |
| Serie histórica | 19 ago → 19 oct 2026, 62 fechas, sin huecos | `historico.csv` |
| Rango de Regular (ventana de 7 cortes) | $15.94 – $29.95 | `fallback.csv` |
| Cobertura del DENUE | 10,667 de 13,854 = 77.0% | `denue.csv` |
| Registros sin equivalencia en catálogo | 5 de 13,854 = 0.04% | `fallback.csv` |

**Trampa de etiquetado.** 96,969 son *registros* (7 cortes × ~13,850), **no
estaciones**. Cuando un conteo cruce varios cortes, la palabra correcta es
"registros" o "comparaciones". Decir "96,969 estaciones" es falso, y la versión
de 41,549 de este mismo error ya llegó a pantalla una vez.

**Trampa del piso de depuración.** El filtro descarta precios bajo $15.00 y el
mínimo real observado es **$15.94**: el margen es de 94 centavos. En la Zona
Libre de la Frontera Norte (IVA 8% y estímulos de IEPS) un cambio de política
fiscal podría meter precios legítimos bajo el piso. Si el conteo de descartados
sube, revisa el umbral antes de culpar a la fuente.
