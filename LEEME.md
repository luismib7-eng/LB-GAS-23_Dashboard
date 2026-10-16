# Parche v13.1 · filtro DENUE y service worker

**Dos archivos. Reemplazan los del repositorio, en la raíz. Nada más se toca.**

Van solo dos porque solo dos cambiaron. Incluir los demás sin cambio añade
riesgo de revertir algo que ya está bien en producción.

```
index.html   →  raíz del repo
sw.js        →  raíz del repo
```

**No subas ningún CSV.** `historico.csv` y `movimientos.csv` son irrecuperables
y el flujo diario regenera el resto.

---

## Qué arregla

En la tabla de estaciones aparecía **"PETRO G SA DE CV — OFICINAS RECO"**.

El DENUE cuelga de algunos permisos de estación registros que no son la
estación: oficinas administrativas, corporativos, inmobiliarias, bodegas. El
tablero los tomaba como nombre comercial y los mostraba al cliente. Son **57 de
10,585** en el corte del 16 de octubre (0.54%).

Se descarta el **registro completo**, no solo el nombre: el domicilio de esos
registros es el de la oficina, no el de la estación, y escribirlo sería peor.

El filtro tiene dos condiciones para no tirar de más. `OFICINA DE GASOLINERA` y
`CORPORATIVO GASOLINERO DEL CARIBE` sí nombran una estación y se conservan: la
segunda condición exige que el nombre NO contenga `GASOLINER`, `ESTACIÓN`,
`SERVICIO`, `COMBUSTIBLE` ni `GASOLINA` antes de descartarlo.

## Qué se declara en pantalla

La línea de calidad ahora dice lo que tiró, en lugar de callarlo:

```
... 10,528 con nombre comercial del DENUE (76%) · 57 registros del DENUE
descartados por no ser la estación
```

Antes decía 10,585 sin aclarar que 57 de ésos eran oficinas. El conteo de
arriba ahora es auditable.

## Service worker

Subió de `lbgas23-v8` a **`lbgas23-v9`**. Sin eso, quien ya tiene el tablero en
caché no recibe el HTML nuevo.

**Recarga dos veces** después de publicar: la primera instala la versión nueva.

## Cómo comprobar que entró

En la línea gris bajo los filtros debe aparecer `57 registros del DENUE
descartados por no ser la estación`. Si no aparece, es caché: cierra la pestaña
y vuelve a abrir.

---

## Lo que sigue pendiente, y no está en este parche

**Cero píxel, cero analítica, cero medio de contacto en la página.** Un prospecto
que abra el Loom, le guste y entre al tablero no tiene por dónde escribirte, y
tú no te enteras de que estuvo ahí. Para el correo no estorba, porque tu firma
lleva tus datos; para pauta en Meta es bloqueante.

Hace falta tu Pixel ID para armarlo.
