# Subcuentas de clientes — Manual de operación

**ENERSO · Licencia Comercializadora Regional**
15 subcuentas incluidas en el contrato.

Este documento explica cómo dar de alta y de baja a los clientes de ENERSO que
recibirán acceso al tablero, y qué ve exactamente cada uno.

---

## 1. Qué es una subcuenta

Cada subcuenta es un tablero propio para una estación de servicio o flota que le
compra combustible a ENERSO. Vive en su propia dirección:

```
https://<dominio>/clientes/enerso/clientes/<slug>/
```

El cliente abre esa dirección y ve **su plaza**: su estación como referencia y los
competidores de su radio, con nombre, distancia y precio.

**Lo que NO ve, por diseño:**

- La Región Occidente completa que sí ve ENERSO.
- Los demás clientes de ENERSO ni sus plazas.
- Cuántos clientes tiene ENERSO ni quiénes son.
- Cualquier estación fuera de su propio radio.
- El desglose regional del reporte comparativo. De ese archivo solo conserva el
  bloque nacional, que es la referencia pública que el tablero usa como
  benchmark.

Esto no es un permiso configurable que se pueda saltar: **la carpeta de cada
cliente contiene físicamente solo las estaciones de su radio.** Aunque alguien
comparta la URL o inspeccione los archivos, del otro lado sigue estando
únicamente su vecindario.

En números reales, comparando el archivo de precios de cada quien: el de ENERSO
pesa 968 KB con 2,834 estaciones; el de la subcuenta de León pesa 10 KB con 173.
La carpeta completa de una subcuenta pesa alrededor de 1.1 MB, pero casi todo es
el tablero mismo (`index.html`, 757 KB) y los iconos, que son idénticos en todas.

---

## 2. El padrón

Todo se controla desde un solo archivo: **`subcuentas.csv`**.

```
slug,nombre,permiso_cre,radio_km,radio_datos_km,zoom,activo
tepa-centro,Servicio Tepatitlán Centro,PL/1234/EXP/ES/2015,5,15,13,si
```

| Columna | Qué poner |
|---|---|
| `slug` | Identificador corto sin espacios ni acentos. Es la carpeta y la URL. |
| `nombre` | Nombre comercial del cliente, tal como lo verá en pantalla. |
| `permiso_cre` | Permiso CRE de **su** estación. Define el centro del recorte. |
| `radio_km` | Radio de competencia que verá en el tablero. Normalmente 5. |
| `radio_datos_km` | Radio de los datos entregados. Por omisión 15. |
| `zoom` | Zoom inicial del mapa. 13 funciona bien para una ciudad. |
| `activo` | `si` genera la subcuenta. `no` la elimina. |

**Por qué `radio_datos_km` es mayor que `radio_km`.** El tablero necesita más
estaciones de las que muestra como competencia directa para que la banda de
precios y el promedio municipal tengan masa estadística. Con 15 km el cliente ve
su competencia de 5 km correctamente clasificada contra un mercado local real.
Si lo bajaras a 5, el percentil se calcularía sobre un puñado de estaciones y
dejaría de significar algo.

---

## 3. Alta de un cliente

1. Consigue el **permiso CRE** de la estación del cliente. Puedes buscarlo en el
   tablero de ENERSO por razón social o municipio: aparece en la columna
   "Permiso CRE".
2. Agrega una fila a `subcuentas.csv` con `activo = si`.
3. Corre el generador:

```bash
python3 preparar_subcuentas.py \
        --origen . \
        --padron clientes/enerso/subcuentas.csv \
        --salida clientes/enerso/clientes \
        --maximo 15
```

4. Publica los cambios. Entrega la URL al cliente.

A partir del siguiente corte diario, su tablero se actualiza solo: el proceso
automático regenera todas las subcuentas con los precios de esa mañana.

**Si el permiso no existe o no tiene coordenadas**, el generador lo dice y no
crea la carpeta, en lugar de entregar un tablero vacío. Revisa el permiso y
vuelve a correrlo.

---

## 4. Baja de un cliente

Un cliente conserva el acceso mientras mantenga relación comercial de compra con
ENERSO. Cuando deja de comprar:

1. Cambia su fila a `activo = no` en `subcuentas.csv`.
2. Corre el mismo comando de arriba.
3. Publica.

**La carpeta se elimina.** La URL deja de existir, no queda una copia vieja
accesible. El generador lo reporta:

```
  BAJA  tepa-centro        carpeta eliminada
```

No borres la fila del padrón: déjala en `no`. Así queda el registro de que ese
cliente tuvo acceso y hasta cuándo, y reactivarlo después es cambiar una palabra.

---

## 5. El tope de 15

El generador **se detiene** si el padrón trae más de 15 subcuentas activas:

```
El padrón trae 17 subcuentas activas y el contrato permite 15.
Marca 'no' en la columna 'activo' a las que sobran antes de continuar.
```

Es deliberado: evita que ENERSO entregue más accesos de los contratados sin
darse cuenta. Si ENERSO necesita más, se amplía el contrato y se cambia
`--maximo`.

---

## 6. Corte de altas

Cada corrida escribe `clientes/enerso/clientes/ALTAS.md` con la tabla de quién
tiene acceso, a qué plaza y con cuántas estaciones. Sirve como comprobante
operativo para ENERSO y para la facturación.

---

## 7. Las tres subcuentas de ejemplo

El padrón se entrega con tres subcuentas de demostración —Morelia, Tepatitlán y
León— para que ENERSO vea el producto funcionando antes de dar de alta a sus
clientes reales. Están construidas sobre estaciones reales del padrón de la CNE,
pero **no son clientes de ENERSO**: son solo un centro geográfico para la demo.

Antes de entregar accesos reales, bórralas del padrón o márcalas en `no`.

---

## 8. Una advertencia honesta sobre el acceso

Hoy la separación entre clientes es **por recorte de datos**, que es la parte
que de verdad protege la información: nadie puede ver lo que no está en su
carpeta. Pero las carpetas son públicas si alguien conoce la URL exacta: no hay
usuario y contraseña.

Para la operación normal esto basta —las URL no son adivinables y cada una solo
contiene la plaza de su dueño—, pero **no prometas confidencialidad por
contraseña** hasta que se implemente el control de acceso. Si ENERSO lo pide, la
ruta más rápida es poner Cloudflare Access delante del sitio sin mover el
alojamiento.
