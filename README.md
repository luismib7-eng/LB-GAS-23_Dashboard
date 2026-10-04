# LB GAS 23 · Monitor de Precios

**Servicio Bautista · Análisis de Precios al Público (SENER / CNE / SAT)**

Tablero web para monitorear precios de gasolina Regular, Premium y Diésel por estación de
servicio. Lee los datos en vivo desde una hoja de Google Sheets publicada como CSV y se
despliega como sitio estático en GitHub Pages.

**Fuente:** Valores estimados por la SENER con información de la CRE/CNE y el SAT.
El precio al público es un promedio de los precios registrados durante el periodo de referencia.

---

## 1. Fuente oficial: el XML de la CNE

El portal de la Comisión Nacional de Energía publica un archivo XML con los precios al público
de todas las estaciones del país:

<https://www.cne.gob.mx/ConsultaPrecios/GasolinasyDiesel/GasolinasyDiesel.html>

El servicio publica **dos archivos, con esquemas distintos**:

```xml
<!-- /publicaciones/prices  ·  precios del dia, identificados por place_id -->
<places>
  <place place_id="11703">
    <gas_price type="regular">22.95</gas_price>
    <gas_price type="premium">27.90</gas_price>
    <gas_price type="diesel">26.99</gas_price>
  </place>
</places>
```

```xml
<!-- /publicaciones/places  ·  catalogo: nombre, permiso CRE y coordenadas -->
<places>
  <place place_id="2039">
    <name>ESTACION HIPODROMO SA DE CV</name>
    <cre_id>PL/658/EXP/ES/2015</cre_id>
    <location><x>-116.9214</x><y>32.47641</y></location>
  </place>
</places>
```

**La llave que une ambos es `place_id`, no el permiso CRE.** El archivo de precios no trae
razon social, ubicacion ni fecha: el catalogo aporta la identidad y la fecha se toma del dia
de la corrida (o con `--fecha`).

El pipeline tambien acepta un esquema anterior que la Comision llego a publicar,
`<precios fecha_generacion><estacion permiso><producto tipo precio>`, y detecta cual de los
dos recibio sin que haya que configurarlo.

El XML trae **permiso y precio, nada más**: no incluye razón social, dirección ni ubicación. Por eso
el proyecto trabaja con dos piezas separadas:

| Pieza | Qué aporta | Con qué frecuencia cambia |
|---|---|---|
| XML de la CNE | Precios del día por permiso | Diaria |
| `catalogo_estaciones.csv` | Permiso → razón social, dirección, municipio, estado, región | Rara vez |

El tablero cruza ambos por el número de permiso. Las estaciones sin coincidencia en el catálogo se
muestran identificadas por su permiso y siguen contando en promedios, mínimos y máximos.

### Arquitectura dual de datos

El tablero recorre las fuentes en orden y se queda con la primera que responda. Si la primaria falla
—red caída, hoja despublicada— pasa sola a la siguiente sin dejar la pantalla en blanco, y el
indicador del encabezado cambia a **Respaldo local** para que la degradación sea visible.

| Orden | Variable en `config.js` | Modalidad | Construye historia |
|---|---|---|---|
| 1 | `SHEET_CSV_URL` | **Cloud (primaria).** Google Sheets alimentado a diario por `AppsScript.gs` | Sí |
| 2 | `CSV_URL` | CSV remoto ya procesado (GitHub Actions u otro servidor) | Solo si acumulas periodos |
| 3 | `XML_URL` | XML oficial alojado en el repositorio, interpretado por el navegador | No |
| 4 | `FALLBACK_CSV` | **Local (secundaria).** `fallback.csv` generado por `xml_a_csv.py` | Solo si acumulas periodos |

La modalidad Cloud es la recomendada: es la única que acumula la serie histórica sin intervención y
la única inmune al bloqueo CORS. La local sirve como respaldo permanente y para trabajar sin Google.

> **El navegador no puede leer el XML directamente del servidor de la CNE.** El portal no envía la
> cabecera `Access-Control-Allow-Origin`, así que apuntar `XML_URL` a `https://www.cne.gob.mx/...`
> falla por CORS. Apps Script no tiene ese problema porque la descarga la hace el servidor de Google.

### Convertir el XML con `xml_a_csv.py`

```bash
python3 xml_a_csv.py precios_2026-08-17.xml --catalogo catalogo_estaciones.csv
# → fallback.csv

# Para acumular varios días en un mismo archivo histórico:
python3 xml_a_csv.py precios_2026-08-18.xml \
        --catalogo catalogo_estaciones.csv \
        --salida historico.csv --acumular
```

### Limpieza que se aplica siempre

Tanto el script como el tablero aplican las mismas dos reglas, así que los números coinciden
sin importar la ruta que uses:

- **Precios fuera de rango.** El XML publica `0.01` o `1.00` cuando la estación no reportó precio.
  Se descartan los valores fuera de `PRICE_MIN`–`PRICE_MAX` (por omisión $15–$45) para que no
  distorsionen promedios ni el mínimo del periodo.
- **Permisos repetidos.** Se conserva el primer registro y solo se completan los productos que le
  falten. En el corte del 17 de agosto de 2026 esto afectó a 35 permisos con precios contradictorios.

En ese mismo corte: 13,860 estaciones en el XML, 13,825 filas útiles, 18 precios descartados. Los
promedios resultantes ($23.69 Regular, $28.51 Premium, $27.02 Diésel) coinciden con los publicados
por Profeco para el periodo, lo que confirma que el criterio de limpieza es el adecuado.

---

## 2. Estructura de la hoja de cálculo

La primera fila debe contener los encabezados. Solo `Estacion` (o `Permiso CRE`) y al menos una
columna de precio son obligatorias; las demás enriquecen el tablero.

| Columna | Obligatoria | Ejemplo | Para qué sirve |
|---|---|---|---|
| `Fecha` | recomendada | `2026-08-18` | Selector de periodo, tendencia histórica y delta vs. periodo anterior |
| `Region` | opcional | `Occidente` | Agrupación de la comparativa y filtro superior |
| `Estado` | opcional | `Jalisco` | Alternativa de agrupación si no hay región |
| `Municipio` | opcional | `Zapopan` | Búsqueda y columna de ubicación |
| `Estacion` | **sí** | `GASOLINERA MARTÍN S.A. DE C.V.` | Razón social de la estación |
| `Permiso CRE` | recomendada | `PL/7773/EXP/ES/2015` | Identificador único y búsqueda |
| `Direccion` | recomendada | `Avenida Adolfo López Mateos Sur No. 1000` | Domicilio en tabla y tarjetas |
| `Regular` | sí* | `22.99` | Precio en MXN/litro |
| `Premium` | sí* | `28.39` | Precio en MXN/litro |
| `Diesel` | sí* | `26.99` | Precio en MXN/litro |
| `Tipo Diesel` | opcional | `DUBA` | Etiqueta en la tabla (DUBA / Automotriz) |
| `Margen` | opcional | `2.06` | Indicador de dispersión, se lee para uso futuro |

\* Al menos una de las tres columnas de precio.

**Formatos aceptados en las celdas de precio:** `22.99`, `$22.99`, `$22.99 - Regular (con un índice
de octano ([RON+MON]/2) mínimo de 87)`. El tablero extrae el número y descarta el texto. Las celdas
vacías, `N/A`, `N/D` o `-` se muestran como *N/D* y quedan fuera de los promedios.

**Nombres de columna flexibles.** El tablero reconoce variantes sin distinguir mayúsculas ni acentos:
`Fecha` / `Periodo` / `Periodo de referencia`; `Estado` / `Entidad`; `Municipio` / `Ciudad`;
`Estacion` / `Razón Social` / `Estación de servicio`; `Permiso CRE` / `Número` / `Número de permiso`;
`Direccion` / `Domicilio`; `Regular` / `Precio Regular`; `Diesel` / `Diésel` / `DUBA`.

Para acumular historia, **agrega filas nuevas con otra `Fecha`** en la misma hoja; no reemplaces las
anteriores. Con dos periodos o más se activan la gráfica de tendencia y el delta de las tarjetas KPI.

Para armar la hoja desde cero, importa `fallback.csv` en Google Sheets (**Archivo → Importar**):
ya trae los encabezados exactos y un periodo completo. El catálogo de estaciones vive aparte, en
`catalogo_estaciones.csv`, y se copia a la pestaña `Catalogo`.

---

## 3. Publicar la hoja como CSV y automatizar la ingesta

1. Abre tu hoja en Google Sheets.
2. **Archivo → Compartir → Publicar en la web**.
3. En el primer desplegable elige **la pestaña específica** con los datos (no "Todo el documento").
4. En el segundo desplegable elige **Valores separados por comas (.csv)**.
5. Pulsa **Publicar** y confirma. Copia la URL que aparece; termina en `output=csv`:

   ```
   https://docs.google.com/spreadsheets/d/e/2PACX-1vQ.../pub?gid=0&single=true&output=csv
   ```

6. Pega esa URL en `config.js`:

   ```js
   SHEET_CSV_URL: "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ.../pub?gid=0&single=true&output=csv",
   ```

Publicar en la web deja la hoja accesible para cualquiera con el enlace: usa una hoja dedicada al
tablero, sin datos reservados. Google tarda unos minutos en reflejar los cambios en el CSV
publicado; el botón **Actualizar** fuerza una nueva lectura del lado del navegador.

Si dejas `SHEET_CSV_URL` vacía, el tablero usa `XML_URL` y, en su defecto, `FALLBACK_CSV`.

### Automatizar la ingesta del XML (Apps Script)

`AppsScript.gs` mantiene la hoja al día sin intervención:

1. En la hoja de cálculo: **Extensiones → Apps Script**.
2. Pega el contenido de `AppsScript.gs`, guarda y confirma la ruta vigente del XML en
   `CONFIG.URL_XML` (tómala del portal de la CNE).
3. Crea dos pestañas: **`Precios`** (destino, la que publicas como CSV) y **`Catalogo`**
   (permiso CRE, razón social, dirección, municipio, estado, región).
4. Ejecuta `actualizarPrecios` una vez para autorizar los permisos y verificar el resultado.
5. Ejecuta `instalarDisparadorDiario` una sola vez: a partir de ahí corre solo cada mañana.

Cada corrida **agrega** el periodo nuevo sin borrar los anteriores, y si la fecha ya estaba cargada
no duplica nada. La escritura se hace por bloques de 5,000 filas con `setValues()` para mantener el
margen frente al límite de seis minutos de ejecución. Como son ~13,800 filas por día, ejecuta
`conservarUltimosPeriodos(60)` de vez en cuando para no acercarte al límite de 10 millones de celdas
de Google Sheets.

### Automatizar sin Google: GitHub Actions

`actualizar-datos.yml` hace lo mismo desde el repositorio: descarga el XML, corre `xml_a_csv.py` y
publica `fallback.csv` con un commit diario.

1. El flujo ya viene en `.github/workflows/actualizar-datos.yml`, que es la ruta que exige GitHub.
   Si subes el proyecto arrastrando carpetas en la web, esa carpeta **no se sube** (el navegador
   ignora las que empiezan con punto): usa `git push`, o créala con **Add file → Create new file**
   escribiendo la ruta completa como nombre.

   > **Si aparece "No event triggers defined in `on`"**, el pegado perdió la sangría: en YAML las dos
   > líneas bajo `"on":` deben ir indentadas. Abre el archivo en GitHub, pulsa el lápiz, borra todo
   > y vuelve a pegar el contenido completo sin reindentar nada. El archivo trae `"on"` entre
   > comillas justamente para evitar que algunos editores lo interpreten como el valor booleano
   > verdadero en lugar de como el nombre del bloque de disparadores.
2. **La variable `URL_XML` es opcional.** El flujo ya trae el endpoint por omisión
   (`https://publicacionexterna.azurewebsites.net/publicaciones/prices`); crea la variable solo si
   necesitas apuntar a otro origen. Un flujo que dependía de una variable inexistente fallaba en
   segundos con `exit code 1`, que es fácil de confundir con un bloqueo de red.
3. **Settings → Actions → General → Workflow permissions**: marca *Read and write permissions*.
4. Pruébalo a mano desde la pestaña **Actions → Run workflow**.

---

## 4. Otros ajustes en `config.js`

| Clave | Qué controla |
|---|---|
| `SHEET_CSV_URL` | CSV publicado de Google Sheets. Tiene prioridad sobre las demás fuentes. |
| `XML_URL` | XML oficial (usa una copia en el repositorio; ver la advertencia de CORS). |
| `CSV_URL` | CSV remoto ya procesado (por ejemplo el que publica GitHub Actions). |
| `FALLBACK_CSV` | Respaldo local dentro del repositorio. Acepta CSV o XML. |
| `CATALOG_CSV` | Catálogo permiso → razón social, dirección y ubicación. `""` lo desactiva. |
| `PRICE_MIN`, `PRICE_MAX` | Rango de precio válido en MXN/litro (por omisión $15–$45). |
| `SEARCH_DEBOUNCE_MS` | Espera del buscador antes de filtrar. |
| `TITLE`, `SUBTITLE` | Encabezado del tablero y título de la pestaña. |
| `LOGO_URL` | Logotipo del encabezado. Si el archivo falta, el título se acomoda solo. |
| `MIS_ESTACIONES` | Permisos y patrones de razón social de tus sucursales; se marcan en el explorador. |
| `REFRESH_MINUTES` | Minutos entre actualizaciones automáticas. `0` las desactiva. |
| `TITLE`, `SUBTITLE` | Encabezado del tablero. |
| `REPO_URL` | Enlace del pie de página. |
| `BENCHMARK` | Referencia nacional que se compara en las tarjetas KPI y se marca en la regla de dispersión. Cambia los valores cuando Profeco publique una nueva edición. |
| `METODOLOGIA` | Leyenda que aparece en el pie y en los tooltips de las tarjetas. |
| `PAGE_SIZE` | Filas por página del explorador. |

---

## 5. Publicar en GitHub Pages

```bash
# 1. Dentro de la carpeta del proyecto
git init
git add .
git commit -m "Tablero de precios de combustibles"
git branch -M main

# 2. Crea el repositorio vacío en github.com y enlázalo
git remote add origin https://github.com/USUARIO/monitor-combustibles.git
git push -u origin main
```

En GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch**,
rama `main`, carpeta `/ (root)`, **Save**. En uno o dos minutos el sitio queda en:

```
https://USUARIO.github.io/monitor-combustibles/
```

Para actualizar el tablero después de un cambio:

```bash
git add . && git commit -m "Ajustes" && git push
```

El archivo `.nojekyll` evita que GitHub Pages procese el sitio con Jekyll.
Los datos **no** requieren un nuevo despliegue: al cambiar la hoja de cálculo, el tablero se
actualiza solo en la siguiente lectura.

---

## 6. Estructura de archivos

```
.
├── index.html                          Estructura del tablero
├── styles.css                          Tokens de diseño, temas claro/oscuro y componentes
├── app.js                              Carga, normalización, KPIs, gráficos y explorador
├── config.js                           Único archivo que necesitas editar
├── .nojekyll
├── README.md
├── logo_lbgas23.png                    Logotipo del encabezado (fondo transparente)
├── favicon.png                         Isotipo de LB GAS 23 para pestaña e ícono de app
├── fallback.csv                        Respaldo local: padrón nacional de 13,825 estaciones
├── catalogo_estaciones.csv             Permiso CRE → razón social y dirección (175 estaciones)
├── xml_a_csv.py                        Convierte el XML oficial a CSV limpio y enriquecido
├── historico.csv                       Promedios diarios por ámbito y producto (gráfica de tendencia)
├── reporte_mercado.csv                 Métricas estilo Profeco: nacional, por marca y por región
├── entidades_mx.geojson                Topología de las 32 entidades para deducir el estado
├── municipios_mx.topojson              Polígonos de los 2,436 municipios para deducir el municipio
├── AppsScript.gs                       Ingesta diaria del XML a Google Sheets
└── .github/
    └── workflows/
        └── actualizar-datos.yml        Ingesta diaria automática desde GitHub Actions
```

Todo vive en la raíz —`index.html` en el primer nivel, que es lo que GitHub Pages espera para
servir desde `/ (root)`— salvo `.github/workflows/`, la única carpeta, y la impone GitHub para los
flujos de Actions.

El tablero interpreta CSV y XML sin dependencias adicionales: el XML se lee con `DOMParser`,
que ya trae el navegador. Las librerías viajan en el repositorio (`leaflet.js`, `leaflet.css`,
`papaparse.min.js`, `chart.umd.min.js`), no por CDN: PapaParse 5.4.1 (lectura de CSV), Chart.js 4.4.1 (gráficos) y Google Fonts
(Archivo, IBM Plex Sans, IBM Plex Mono). Sin proceso de compilación: el sitio funciona abriendo
`index.html` desde un servidor estático.

> Para probarlo en tu equipo: `python3 -m http.server 8000` y abre `http://localhost:8000`.
> Abrir el archivo con doble clic (`file://`) no funciona porque el navegador bloquea la lectura
> del CSV local.

---

## 7. Identidad visual

La paleta parte del logotipo de LB GAS 23: azul marino petróleo (`--brand: #1E3A5F`) como color
institucional, y los tres productos conservan su código de lectura —esmeralda para Regular, rubí
para Premium y ámbar para Diésel— porque son la clave de interpretación de todo el tablero, no
decoración.

- **Modo oscuro:** fondo `#0A111E`, tarjetas `#131F33`, superficies elevadas `#1C2C47`.
- **Modo claro:** fondo `#F0F4F8`, tarjetas blancas y filo inferior azul de marca en el encabezado.
- **Tarjetas y paneles:** filo superior con degradado azul corporativo que se desvanece a la derecha.
- **Logotipo:** `logo_lbgas23.png` viene recortado y con fondo transparente, así que la placa azul
  se apoya limpiamente en ambos temas. Para sustituirlo basta con reemplazar el archivo o cambiar
  `LOGO_URL`; si falta, el encabezado se acomoda sin dejar hueco.

### Marcar tus sucursales

Las estaciones propias aparecen en el explorador con el distintivo **Sucursal propia**, realce azul
y filo lateral. Se declaran en `config.js`:

```javascript
MIS_ESTACIONES: {
  permisos: ["PL/12345/EXP/ES/2015"],       // coincidencia exacta (recomendado)
  patrones: ["LB GAS", "SERVICIO BAUTISTA"] // texto contenido en la razón social
}
```

**Los permisos son la única vía confiable.** Comprobado contra el catálogo nacional completo: no
existe ninguna razón social que contenga "LB GAS", y "Servicio Bautista" solo coincide con
`PL/4799/EXP/ES/2015`, una estación de Oaxaca que no es tuya. Por eso `patrones` viene vacío.

---

## 8. Módulos de inteligencia comercial

### Filtros de Estado y Municipio en cascada

Sustituyen al antiguo selector único de Región. El municipio solo lista los del estado elegido, y
ambos se alimentan de las columnas `Estado` y `Municipio` del catálogo.

Los selectores **nunca se deshabilitan**: las estaciones sin ubicación se agrupan en una opción
propia, *Sin ubicación (n)*, que también funciona como filtro. Así puedes aislar exactamente las que
faltan por catalogar.

**Cuando el catálogo no trae ubicación**, el tablero intenta deducirla del domicilio, pero solo
acepta la coincidencia si aparece donde un domicilio mexicano realmente codifica la localidad:

- en los dos últimos segmentos separados por coma — *"Av. Vallarta 1234, Col. Americana,
  Guadalajara, Jalisco"*;
- después de un marcador explícito — *"Municipio de Zapopan"*, *"Mpio. Tala"*.

Todo lo demás se ignora deliberadamente, porque en México las ciudades dan nombre a calles y
carreteras: *"Avenida Lázaro Cárdenas"* está en Guadalajara, no en Lázaro Cárdenas, y
*"Carretera Guadalajara – Nogales"* puede estar a 200 km de Guadalajara. Una ubicación equivocada
contamina el promedio local, el semáforo y el simulador, así que el motor prefiere no responder.

Lo inferido se marca con **≈** en la columna Ubicación y se declara como *Inferido del domicilio*
en la exportación. **La ruta confiable es llenar `Estado` y `Municipio` en
`catalogo_estaciones.csv`**, que además activa la comparativa por municipio.

Para ampliar la cobertura del motor, agrega entradas al diccionario `MUNICIPIOS` en `app.js`
(clave en minúsculas y sin acentos, valor el estado).

`config.js` incluye `ESTADO_POR_DEFECTO` para asignar un estado a todo lo que quede sin ubicación.
Viene vacío a propósito: si lo llenas, las ~13,650 estaciones sin dato caen bajo ese estado y el
"promedio estatal" contra el que se mide el semáforo deja de ser el de tu plaza para volverse el
nacional disfrazado. Lo asignado se exporta marcado como *Asignado por omisión*.

### Mercado local: radio, municipio, estado, país

El promedio contra el que se mide cada estación se elige en este orden, quedándose en el primero que
tenga al menos dos estaciones:

1. **Radio** — cuando el catálogo trae `Lat` y `Lon`. `RADIO_KM` en `config.js` (5 km por omisión;
   3–5 en zona urbana, 15–25 en carretera). Es la definición más fiel de competencia: quien está a
   pocos kilómetros, sin importar el límite municipal. Se indexa en una rejilla espacial para no
   comparar cada estación contra las 13,800 restantes.
2. **Municipio** → 3. **Estado** → 4. **Nacional**.

El tooltip de cada diferencial dice qué universo se usó y con cuántas estaciones.

### Semáforo comercial y diferencial vs. promedio local

La tabla incluye la columna **Δ vs. promedio local** del producto seleccionado:

- 🟢 **verde**: por debajo del promedio de su mercado — estrategia de volumen;
- 🔴 **rojo**: por encima — margen alto con riesgo de perder volumen;
- gris: en el promedio.

El promedio se calcula por municipio y degrada a estado y luego a nacional cuando no hay al menos
dos estaciones en el nivel más fino. El tooltip de cada valor dice contra qué universo se comparó y
con cuántas estaciones. **El promedio siempre se calcula con el padrón completo del periodo**, aunque
estés filtrando: aislar tus estaciones no debe mover la referencia de mercado.

### Interruptor Mercado total / Solo mis estaciones

Un clic aísla las estaciones declaradas en `MIS_ESTACIONES`. Queda deshabilitado mientras no haya
ninguna identificada, y el conteo junto al interruptor te dice cuántas reconoció.

### Simulador táctico de precios

Panel colapsable. El buscador acepta **cualquier estación del padrón** —por permiso CRE (`PL/...` o
`CNE/PL/...`), razón social, municipio o dirección—; sin búsqueda abre con las tuyas, marcadas con ★.
Mueves el precio con los botones de ±0.10 y ±0.20 o escribes uno, y responde al instante:

- cómo cambia su lugar en el ranking del municipio — *"Pasarías del lugar 4 al 2 más económico de
  Zapopan"*;
- la brecha resultante contra la estación más barata de la zona y contra el promedio local;
- el **margen proyectado** en $/L: cuánto ganas o cedes por litro vendido frente al precio de hoy.

La estación no compite consigo misma: se excluye del ranking antes de calcular. Si el municipio no
está confirmado, el panel avisa que la comparación se hizo contra un universo más amplio.

### Competencia directa por marca

Tarjetas con el precio promedio de las marcas vigiladas (`MARCAS_COMPETENCIA` en `config.js`) dentro
de la selección activa, ordenadas de más barata a más cara y contrastadas contra el promedio de la
zona filtrada. La marca se reconoce por la columna `Marca` del catálogo y, en su defecto, por la
razón social, **siempre por palabra completa**.

Esa última precisión no es cosmética: buscar por subcadena convertía cada *INMOBILIARIA* en una
estación Mobil (166 falsos positivos) y marcaba a *MARCOFAN* como Arco. Aun con palabra completa, el
catálogo de la CNE publica la sociedad mercantil y no la bandera, así que quedan casos irreducibles
como *Servicio Ciudad Pemex* (un municipio de Tabasco) u *Honestidad Total*. La lista por omisión se
limita a marcas que operan con razón social propia; para una vigilancia seria, llena la columna
`Marca` en `catalogo_estaciones.csv`.

### Exportador de la vista filtrada

El botón **Exportar vista** genera un CSV con lo que estás viendo —filtros, búsqueda y orden
incluidos— más las columnas calculadas: promedio local, alcance del promedio, diferencial, posición
comercial, origen de la ubicación y si es sucursal propia. Lleva BOM UTF-8, así que Excel respeta
los acentos, y el nombre del archivo recoge producto, periodo y filtros.

---

### Mis estaciones monitoreadas (hasta 5)

El botón **★ Mis estaciones** del encabezado abre un buscador sobre el padrón completo: eliges hasta
cinco permisos y la selección se guarda en `localStorage`, así que persiste en ese navegador sin
tocar código. `MIS_ESTACIONES.permisos` en `config.js` funciona como semilla inicial; a partir de la
primera selección manda lo guardado.

Con el interruptor **Solo mis estaciones** activo aparece un resumen comparativo: precio, promedio de
su radio, diferencial, lugar dentro del radio y número de competidores. En el **simulador**, tus
estaciones encabezan siempre la lista.

### Reporte de mercado estilo "Quién es Quién en los Precios"

Panel con dos vistas:

- **Por marca** — precio promedio de cada marca reconocida y su diferencial contra el precio más bajo
  del periodo.
- **Por región** — extremos *precios caros* y *precios justos* de cada una de las 8 regiones de la
  Política Pública de Almacenamiento Mínimo, más una tabla de promedio, mínimo, máximo y brecha.

Las regiones son las oficiales: Noroeste (BC, BCS, Son, Sin, Nay), Norte (Chih, Dgo), Noreste (Coah,
NL, Tamps, SLP), Occidente (Zac, Ags, Jal, Gto, Mich, Col), Centro (Qro, Hgo, Tlax, Pue, Mor, EdoMex,
CDMX), Golfo (Ver, Tab), Sur (Gro, Oax, Chis) y Sureste (Camp, Yuc, Q. Roo).

> **Sobre el margen de ganancia.** Profeco lo publica con estimaciones de la SENER —precio de
> referencia en TAR, IEPS y estímulos fiscales— que **no vienen en las publicaciones de la CNE**. Con
> los datos disponibles no es posible reconstruirlo sin inventar supuestos, así que en su lugar se
> reporta el **diferencial contra el precio más bajo del periodo**, que sí es medible, y se etiqueta
> como tal en el gráfico, en la tabla y en el CSV. Si consigues la serie de precios de referencia en
> TAR, el cálculo del margen real se agrega en una tarde.

`xml_a_csv.py --reporte reporte_mercado.csv` escribe las mismas métricas como archivo, un renglón por
bloque, producto y fecha (~35 KB al año). El panel del tablero las recalcula en vivo desde el padrón.

### Estado y municipio de cada estación: punto en polígono

El catálogo de la CNE trae coordenadas pero ni entidad ni municipio.

```bash
python3 xml_a_csv.py precios_del_dia.xml --catalogo places.xml \
        --geojson entidades_mx.geojson \
        --municipios municipios_mx.topojson \
        --exportar-catalogo catalogo_estaciones.csv --salida fallback.csv
```

`--municipios` lee un TopoJSON de los 2,436 municipios: decodifica los arcos cuantizados, arma los
polígonos e indexa sus bounding boxes en una rejilla para no recorrerlos todos por cada estación.
Resultado: **14,158 de 15,034 estaciones con municipio**, en menos de un segundo. Comprobado contra
puntos conocidos: Cancún → Benito Juárez, Guadalajara → Guadalajara, Tlajomulco → Tlajomulco de
Zúñiga.

`--geojson` hace lo propio con el estado sobre la topología de las 32 entidades, y de ahí sale la
región.

Resultado del estado sobre el catálogo real: **14,936 de 15,034 asignadas**, de las cuales 133 por cercanía
—estaciones costeras que caen fuera del polígono simplificado, a las que se asigna la entidad más
próxima dentro de 20 km— y 98 sin asignar. Cerca de los límites estatales el polígono simplificado
puede equivocarse; si una estación tuya aparece en el estado vecino, corrígela a mano en
`catalogo_estaciones.csv`: el valor capturado siempre gana sobre el deducido.

### Los dos archivos de datos y por qué son dos

| Archivo | Qué contiene | Tamaño por corte | Para qué sirve |
|---|---|---|---|
| `fallback.csv` | Padrón completo: una fila por estación | ~1.6 MB (13,825 filas) | Tabla, KPIs, dispersión, semáforo, simulador, panel Profeco |
| `historico.csv` | Promedios nacional, por estado y por región | ~6 KB | Gráfica de tendencia y delta de las KPIs |
| `reporte_mercado.csv` | Métricas por marca y región | ~2 KB | Registro semanal del reporte |

El flujo acumula en los tres con ventanas distintas: `--conservar 7` para el padrón (una semana móvil)
y `--historico-conservar 120` para los promedios. **No es posible guardar 60 cortes completos**: con
la razón social incluida, cada corte pesa 1.6 MB, así que 60 serían unos 95 MB que el navegador
tendría que descargar y recorrer en cada carga. La memoria larga vive en `historico.csv`, que con 120
cortes no llega a 600 KB, y la gráfica de tendencia se alimenta de ahí en cuanto tiene más historia
que el padrón.

Si prefieres la serie completa por estación, sube `--conservar` y apunta `FALLBACK_CSV` al archivo
acumulado; el tablero usa los periodos del padrón cuando tiene más historia que `historico.csv`.

### Por qué el histórico no baja al municipio

`historico.csv` guarda los ámbitos nacional, estatal y regional. El municipal se excluye a propósito:
con 1,406 municipios el archivo pasa de 6 KB a 556 KB por corte, y a 120 cortes serían 33 MB que el
navegador tendría que descargar y recorrer en cada carga. Cuando filtras un municipio, la gráfica de
tendencia degrada a la serie de su estado y lo declara en el subtítulo.

### Ejecutar el pipeline a mano con acumulación

```bash
python3 xml_a_csv.py precios_del_dia.xml \
        --catalogo catalogo_estaciones.csv \
        --salida fallback.csv --acumular --conservar 3 \
        --historico historico.csv --historico-conservar 120
```

Si la fecha del XML ya está cargada, no duplica nada y lo dice en la salida.

### Catálogo desde el XML de estaciones de la CNE

El mismo servicio que publica los precios publica el catálogo de estaciones:

```bash
curl -fsSL -o places.xml "https://publicacionexterna.azurewebsites.net/publicaciones/places"

python3 xml_a_csv.py precios_del_dia.xml \
        --catalogo places.xml \
        --exportar-catalogo catalogo_estaciones.csv \
        --salida fallback.csv
```

Eso convierte el XML de estaciones en tu `catalogo_estaciones.csv` y puede llevarte de 175 permisos
identificados a casi 14,000, de golpe.

**Probado contra el archivo real** (edición del 18 de agosto de 2026): 15,034 estaciones, todas con
razón social y 15,029 con coordenadas. El cruce contra el padrón de precios da **13,825 de 13,825**.

El esquema publicado es:

```xml
<places>
  <place place_id="2039">
    <name>ESTACION HIPODROMO SA DE CV</name>
    <cre_id>PL/658/EXP/ES/2015</cre_id>
    <location><x>-116.9214</x><y>32.47641</y></location>
  </place>
</places>
```

No incluye domicilio, municipio ni estado: **solo razón social y coordenadas**. Por eso el mercado
local se calcula por radio (sección 8) y las columnas `Estado` y `Municipio` del catálogo siguen
disponibles para que las llenes si las necesitas para los filtros.

El lector es tolerante con el esquema por si cambia: recorre cualquier elemento que contenga una
cadena con forma de permiso —en atributo o en hijo— y toma nombre, domicilio, municipio, estado y
coordenadas de los hijos o atributos cuya etiqueta lo sugiera, ignorando espacios de nombres,
mayúsculas, acentos y guiones bajos (`CreId`, `cre_id` y `{ns}CRE-ID` son la misma clave). El patrón
de permiso cubre las cinco variantes observadas: `EXP/ES`, `EXP/ESA` (autoconsumo), `EXP/ES/MM`,
`TRA/OM` y el prefijo `CNE/` de los permisos emitidos desde 2025.

---

## 9. Qué muestra cada bloque

- **Tarjetas KPI.** Promedio de cada producto en el periodo y filtro activos, número de estaciones
  con precio, cambio contra el periodo anterior y diferencia contra la referencia nacional.
- **Precio más bajo / más alto.** Estación en los extremos del producto seleccionado.
- **Regla de dispersión.** Una marca por estación entre el mínimo y el máximo, con la mediana, la
  banda P25–P75 y la referencia nacional. Muestra de un vistazo qué tan concentrado está el mercado.
- **Tendencia por periodo.** Promedio de los tres productos en cada fecha cargada.
- **Comparativa.** Promedio por región, estado, municipio o marca, según las columnas disponibles.
  Con más de catorce grupos muestra los siete más altos y los siete más bajos.
- **Distribución de precios.** Cuántas estaciones caen en cada rango.
- **Explorador.** Búsqueda por estación, permiso CRE, municipio o dirección; orden por cualquier
  columna; paginación; etiquetas de mínimo, máximo y tipo de diésel.

**Notas:** excluye zonas fronterizas con estímulo fiscal. El indicador de ganancia de las compañías
importadoras incluye el margen al mayoreo e incluye descuentos en TAR.

---

## 10. Flujo de comandos

### Actualizar los datos (modalidad local)

```bash
# 1. Descarga el XML del día
curl -fsSL -o precios_del_dia.xml "https://publicacionexterna.azurewebsites.net/publicaciones/prices"

# 2. Conviértelo y acumula la serie
python3 xml_a_csv.py precios_del_dia.xml --catalogo catalogo_estaciones.csv \
        --salida fallback.csv --acumular --conservar 3 \
        --historico historico.csv --historico-conservar 120

# 3. Revísalo en local antes de publicar
python3 -m http.server 8000    # abre http://localhost:8000

# 4. Publica
git add fallback.csv historico.csv
git commit -m "Precios $(date +%F)"
git push
```

Para acumular la serie histórica en lugar de reemplazar el corte del día, cambia el paso 2 por:

```bash
python3 xml_a_csv.py precios_del_dia.xml --catalogo catalogo_estaciones.csv \
        --salida historico.csv --acumular
```

y apunta `FALLBACK_CSV: "historico.csv"` en `config.js`.

### Primer despliegue

```bash
git init
git add .
git commit -m "Monitor de precios de combustibles"
git branch -M main
git remote add origin https://github.com/USUARIO/monitor-combustibles.git
git push -u origin main
```

Luego **Settings → Pages → Deploy from a branch → `main` / `(root)`**.

### Cambios posteriores al tablero

```bash
git add . && git commit -m "Ajustes" && git push
```

Con la modalidad Cloud no hace falta ninguno de estos pasos para los datos: al actualizarse la hoja,
el tablero la lee en la siguiente sincronización.

---

## 11. Control de calidad

Reglas que el código sostiene y cómo se verifican.

| Regla | Dónde vive | Verificación |
|---|---|---|
| Todo cruce de permisos usa la clave canónica | `permitKey()`: mayúsculas, sin espacios, sin prefijo `CNE/` | Aplicada en el deduplicado, el cruce con catálogo, "mis estaciones", el simulador y el índice de búsqueda |
| Precios validados con `isFinite` y dentro de $15–$45 | `toNumber()` | Los valores centinela del XML (0.01, 1.00) se descartan y se cuentan en la nota superior |
| Los nulos nunca entran a un promedio | `pricesOf()`, `avg()`, `quantile()` | Ningún agregado asume 0 en celda vacía |
| Menos de 2 datos degrada sin error | Dispersión, comparativa, histograma, marcas | Cada bloque muestra su estado vacío explicativo |
| Los nulos van al final al ordenar | comparador de `tableRows()` | Verificado en ambos sentidos y en las tres columnas de precio |
| Toda mutación del set filtrado reinicia la página | manejadores de periodo, estado, municipio, producto, búsqueda, interruptor y gestor | Probado desde la página 41: al filtrar cae a "Página 1 de 6" |
| `localStorage` siempre entre `try/catch` | caché, tema y "mis estaciones" | Con `localStorage` bloqueado, el tablero carga igual |
| Copia guardada con versión y validación de forma | `CACHE_KEY` incluye `:v3`; `readCache()` valida la primera fila | Una copia corrupta se ignora y la carga sigue |
| Toda promesa con `.catch` | cadena de fuentes, catálogo, histórico | Si la fuente primaria falla, degrada al respaldo local |

Los estados vacíos son parte del diseño, no un pendiente: cuando un bloque no tiene datos
suficientes explica qué falta y dónde capturarlo, en lugar de mostrar un cero que se lea como dato.

---

## 12. Respuesta a la auditoría externa

| Hallazgo | Resolución |
|---|---|
| Alias cortos de permiso en `AppsScript.gs` descartaban el catálogo en silencio | Ampliados para cubrir lo mismo que `FIELD_ALIASES` de `app.js` |
| `periodoYaCargado_` solo revisaba las últimas 20,000 filas | Revisa la columna completa: reordenar la hoja ya no puede duplicar un corte |
| `computeMercado()` reconstruía la rejilla espacial en cada cambio de vista | Memorizado por firma (periodo + filas + radio): los filtros cosméticos ya no lo recalculan |
| El interruptor "Solo mis estaciones" no respondía sin estaciones configuradas | Ahora abre el gestor con ese clic |
| Gráficas ocultas del panel Profeco | Ya era así: `renderProfeco()` solo dibuja la vista activa |
| `saveCache` desactiva el modo offline con el padrón completo | **Decisión consciente, no corregida.** El padrón pesa ~3 MB en JSON y el límite de `localStorage` es de 5 MB; migrar a IndexedDB agregaría una capa asíncrona por un beneficio marginal, ya que el respaldo local del repositorio cumple la misma función sin código extra |
| Rigor de `esc()` en las plantillas HTML | Revisado: todos los campos de origen externo pasan por `esc()` |

---

## 13. Comportamiento en teléfono y tableta

El corte está en **1080 px**: por debajo, el tablero cambia de comportamiento.

- **La barra superior deja de ser fija.** Con todos los filtros desplegados llegaba a ocupar 594 px
  de una pantalla de 844: la mitad del teléfono se iba en encabezado antes de ver un solo dato.
- **Los filtros se pliegan** tras el botón **☰ Filtros**. Cerrados, una línea bajo la barra resume
  lo aplicado — *"Regular · 18 ago 2026 · Jalisco · Zapopan"*— para que nunca navegues sin saber qué
  estás viendo. Al elegir un municipio el panel se cierra solo y devuelve la pantalla.
- **Una sola columna** en tarjetas KPI, gráficas, simulador y tablas regionales.
- **Las tablas se desplazan a lo ancho** dentro de su propio contenedor, con inercia en iOS. Cuando
  hay columnas fuera de vista aparece el aviso *"Desliza para ver los precios →"* y un velo en el
  borde derecho, que desaparecen al primer desplazamiento.
- **El modal usa `dvh`** en lugar de `vh`: en Safari de iOS, `100vh` incluye las barras del
  navegador y recortaba el contenido al aparecer o desaparecer.

Medición del alto del encabezado, antes y después:

| Dispositivo | Antes | Ahora |
|---|---|---|
| iPhone SE (375 px) | 558 px | 147 px |
| iPhone 14 (390 px) | 594 px | 186 px |
| iPad mini (768 px) | 280 px | 144 px |
| iPad Pro vertical (1024 px) | 332 px | 183 px |

Ningún ancho probado —375, 390, 430, 768, 1024 px— produce desplazamiento horizontal de página:
`scrollWidth` coincide con el ancho del viewport en todos. En escritorio no cambia nada: la barra
sigue fija, los filtros siempre visibles y el botón ☰ oculto.

---

## 14. Mapa, briefing y simulador financiero

### Mapa táctico de competencia

Leaflet 1.9.4 por CDN con `preferCanvas: true`. Dibuja solo las estaciones **dentro del encuadre
visible**, con tope de `MAPA_MAX_PUNTOS` (2,500 por omisión): pintar 14,000 puntos vectoriales
tumbaría cualquier teléfono. Al acercar o filtrar por estado entran todas las de la zona, y cuando el
tope recorta algo el pie del mapa lo dice.

- **Competencia:** círculos con el color del semáforo local — verde por debajo del promedio de su
  radio, rojo por encima, gris en el promedio.
- **Estaciones propias:** marcador azul de marca con halo pulsante y ★, más un círculo punteado con
  el radio de competencia (`RADIO_KM`).
- **Popup:** razón social, permiso, marca, ubicación, los tres precios vigentes y el diferencial
  contra su radio.
- Los mosaicos son de OpenStreetMap, con su atribución obligatoria. En modo oscuro se aplica un
  filtro al mapa base para que no compita con los datos.

> Un detalle que costó encontrar: abrir un popup hace que Leaflet desplace el mapa (`autoPan`), lo
> que dispara `moveend` y provocaba un repintado que borraba el marcador —y con él, el popup recién
> abierto—. Ahora no se repinta mientras haya un popup abierto, y el repintado pendiente se ejecuta
> al cerrarlo.

### Briefing ejecutivo

Tarjeta colapsable al inicio del tablero. Por cada estación propia genera tres líneas:

1. Cuántos competidores de su radio movieron precio contra el corte anterior.
2. Su posición: diferencial contra el promedio del radio y lugar dentro de él.
3. La acción: el ajuste mínimo en centavos para entrar al top 3, o —si ya está ahí— cuánta holgura
   tiene antes de perder posición, que es margen que puede recuperar.

Con la venta diaria capturada, la recomendación también expresa el ajuste en pesos por día.

### Simulador financiero

Tres campos nuevos, guardados en el navegador: **venta diaria en litros**, **costo por litro**
(opcional) y **litros extra esperados**.

| Con venta diaria | Con costo por litro |
|---|---|
| Δ por litro, ingreso diario y proyección mensual | Utilidad bruta diaria y mensual, y punto de equilibrio |

El punto de equilibrio responde la pregunta que importa al bajar el precio: *para no perder utilidad
bajando $0.10/L necesitas vender 1,112 litros más al día (7% sobre tu volumen actual)*.

> **Sin costo por litro, el tablero reporta ingreso, no utilidad, y lo dice explícitamente.** El
> costo en TAR más flete no está en ninguna publicación de la CNE ni del SAT; suponerlo convertiría
> una cifra dura en una estimación disfrazada.

### Instalación como app (PWA)

`manifest.json` con iconos de 192, 512 y 512 maskable, más las meta de Apple. En iPhone:
**Compartir → Añadir a pantalla de inicio**; el tablero abre en modo `standalone`, sin barras de
Safari, con el isotipo de LB GAS 23 como ícono.

No se incluye *service worker*: sin él no hay modo offline, pero tampoco una capa de caché que se
quede con una versión vieja del tablero sin avisar. El respaldo local del repositorio ya cubre la
continuidad de datos.

---

## 15. Resiliencia offline y auditoría de la iteración

### Service worker

`sw.js` aplica una estrategia distinta según el recurso:

| Recurso | Estrategia | Razón |
|---|---|---|
| Cascarón (HTML, CSS, JS, librerías, iconos) | Stale-while-revalidate | Arranque instantáneo y actualización en segundo plano |
| Datos (CSV, XML, GeoJSON) | Network-first con respaldo de caché | Nunca un precio viejo teniendo red; sin red, el último corte |
| Mosaicos del mapa | Cache-first con tope de 300 piezas | Evita volver a bajar el mapa base y no llena el disco |

Cuando el tablero arranca sin conexión, el indicador dice **"Sin conexión · copia guardada"** en
lugar de fingir que está sincronizado. Probado: con la red apagada, carga completa en 3.6 segundos
desde la caché.

Para publicar una versión nueva basta con subir `VERSION` en `sw.js`. Las pestañas abiertas reciben
un aviso flotante — *"Hay una versión nueva del tablero"* con un botón — y **nunca se recarga sin
que el usuario lo autorice**.

El ciclo está probado de extremo a extremo: con `VERSION` en `v1` cargado y la copia en disco subida
a `v2`, el aviso aparece, el worker nuevo queda en espera, y al aceptar toma control, borra las
cachés `v1-*` y deja únicamente `v2-cascaron`, `v2-datos` y `v2-mapa`, con el tablero operativo.

Tres detalles del ciclo que cuestan encontrar y quedaron resueltos:

- **`skipWaiting()` no va en `install`.** Si el worker nuevo tomara control de inmediato, una pestaña
  abierta seguiría ejecutando el JS anterior mientras recibe archivos nuevos: la forma más silenciosa
  de romper un tablero. Solo se ejecuta cuando llega el mensaje del botón.
- **El destinatario del mensaje se resuelve al hacer clic**, no al registrar. Capturarlo antes puede
  acabar hablándole al worker que ya está activo, donde `skipWaiting()` no hace nada y la
  actualización se queda esperando para siempre. Este fallo estuvo presente y se detectó
  instrumentando el evento `activate` para comprobar que nunca se disparaba.
- **La recarga la dispara `controllerchange`**, no el clic. Recargar antes de que el worker nuevo
  tome el control deja la página con el anterior y el aviso reaparece.

### Librerías locales

Leaflet, PapaParse y Chart.js dejaron de cargarse desde `cdnjs` y viajan en el repositorio (380 KB en
total). Elimina la dependencia de una red externa, permite que el service worker las precargue y
vuelve innecesario el `integrity` de SRI: el archivo servido es el que está versionado en Git.

### Correcciones de esta iteración

| Hallazgo | Origen | Estado |
|---|---|---|
| La rejilla espacial perdía competidores del borde este-oeste del radio | Detectado al verificar la observación sobre Haversine | Corregido: el ancho de celda en longitud se calcula por latitud. Contraste contra fuerza bruta sobre 400 estaciones: 0 discrepancias |
| Venta bajo costo mostraba proyecciones sin advertencia | Observación externa | Alerta explícita antes de cualquier cifra, con la pérdida diaria y la aclaración de que ningún volumen la compensa |
| Pérdidas pintadas de verde en las tarjetas financieras | Detectado al revisar la captura | En el bloque financiero el color sigue al dinero: ganar verde, perder rojo. En las de posición, verde sigue significando estar por debajo del mercado |
| `money()` imprimía `$-0.50` | Detectado en la misma revisión | Ahora `−$0.50` |
| `▲ +0.00` cuando la diferencia era de milésimas | Detectado en pruebas | Menos de medio centavo se lee "Sin cambio" |
| Fórmula de distancia | Observación externa | Ya era Haversine; se confirmó y se documentó |
| Coordenadas nulas o `(0,0)` | Observación externa | Ya se descartaban en `coord()`; las estaciones sin coordenada no entran al radio ni al denominador del briefing |
| El botón de actualizar le hablaba al worker activo, no al que esperaba | Detectado al verificar la observación sobre `skipWaiting` | Corregido: el destinatario se resuelve al hacer clic y la recarga espera a `controllerchange` |
| `mapaPintando` podía quedar en `true` si algo fallaba a media pintada | Detectado al revisar la bandera del popup | `try/finally`: el mapa nunca queda congelado sin error visible |
| La pausa del repintado leía `mapa._popup`, API privada de Leaflet | Observación externa | Bandera propia con los eventos públicos `popupopen` y `popupclose` |
| Briefing sin estaciones: mensaje sin salida | Observación externa | Ahora incluye el botón **Abrir Mis estaciones**, que lleva directo al gestor |

### Elasticidad sugerida

El simulador propone litros extra a partir de un supuesto configurable
(`ELASTICIDAD_PCT_POR_10_CENTAVOS`, 2% por omisión) con un botón para aplicarlo. Va etiquetado como
**supuesto del sector, no medición de tu plaza**: el campo manual sigue siendo la vía correcta cuando
tengas tu propio dato.

---

## 16. Si el flujo de GitHub Actions falla

El paso **Descargar el XML oficial** imprime el código HTTP y el tamaño recibido antes de procesar
nada, y valida tres cosas: que el código sea 200, que pese más de 100 KB y que el contenido empiece
con `<precios`. Si algo no cuadra, la corrida **termina en verde** con un aviso y sin tocar los datos
publicados: el tablero sigue sirviendo el último corte bueno.

Lee el resumen de la corrida y ubica el caso:

| Lo que ves | Qué significa | Qué hacer |
|---|---|---|
| `HTTP 200 · ~2,500,000 bytes` | Todo bien | Nada |
| `HTTP 000 · 0 bytes` | No hubo conexión, DNS o tiempo agotado | Reintentar a mano; si se repite varios días, pasar al plan B |
| `HTTP 403` y unos pocos KB de HTML | Un WAF respondió un reto en vez del archivo | Plan B |
| `HTTP 404` | Cambió la ruta del endpoint | Confirmar la ruta vigente en el portal y ponerla en la variable `URL_XML` |
| Falla antes de imprimir nada | Error de permisos o de sintaxis del flujo | Revisar *Workflow permissions* en Settings |

**Plan B (Apps Script).** `AppsScript.gs` hace la misma ingesta desde los servidores de Google, con
otro rango de direcciones y otra ruta de salida. Si el origen bloquea a GitHub pero no a Google, esa
vía sigue funcionando sin cambiar el tablero: basta con publicar la hoja como CSV y poner la URL en
`SHEET_CSV_URL` dentro de `config.js`.

**Plan C (equipo local).** El mismo comando del flujo, corrido desde tu equipo y con `git push`. Es
la vía más simple si el origen solo acepta direcciones residenciales mexicanas.

```bash
curl -fsSL -o precios_del_dia.xml "https://publicacionexterna.azurewebsites.net/publicaciones/prices"
python3 xml_a_csv.py precios_del_dia.xml --catalogo catalogo_estaciones.csv \
        --salida fallback.csv --acumular --conservar 7 \
        --historico historico.csv --historico-conservar 120 \
        --reporte reporte_mercado.csv
git add fallback.csv historico.csv reporte_mercado.csv && git commit -m "Precios $(date +%F)" && git push
```

Las tres vías escriben exactamente los mismos archivos, así que puedes cambiar de una a otra sin
tocar el tablero.
