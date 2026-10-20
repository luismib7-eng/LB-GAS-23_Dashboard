# Contrainteligencia · Signal Fuels (Cassiopeia)

`https://cassiopeiamx.com/signal-fuels` — auditado el 20 de octubre de 2026
contra el PDF de su sitio, fuentes públicas y los archivos del repositorio.

**Es un competidor nuevo y distinto de `fuelpricing.com.mx`.** Ahora son dos
identificados, y este es el que se le parece más a LB GAS 23.

---

## 1. Lo que cobran, que es el dato más accionable

| Plan | Precio | Nota |
|---|---|---|
| Semanal | **$689 MXN / semana** | Pago único, 7 días, sin renovación |
| Profesional | **$2,699 MXN / mes** | El que recomiendan |
| Unlimited | A cotizar | +5 licencias, API, reportes |

Para comparar: `fuelpricing.com.mx` cobra **$4,930/mes por usuario**. Tu Plan
Red arranca en $1,500 y el Plan Grupo son $5,000.

**Signal Fuels se metió debajo de fuelpricing y encima de tu entrada.** Eso
cambia la conversación de precio: ya no eres el caro contra uno solo; eres el
de entrada accesible en un rango donde ya hay tres niveles.

El plan de $689 por una semana es su arma real. Es una prueba pagada que
compra la objeción "déjame verlo primero" sin comprometer un mes.

---

## 2. Lo que venden

- Precios TAD (terminal) diarios e histórico — **78+ terminales**
- Precios en bomba — dicen **13,000+** en un lado de la página y
  **más de 14,000** en otro; su propio material no concuerda
- Mapa, gráficas y análisis de competencia por zona y radio
- Padrón de gasolineras y terminales
- Indicadores WTI y USD/MXN
- **Asistente de IA**: 100 consultas en el semanal, 400 al mes en el profesional

---

## 3. Dónde el dictamen recibido se equivocó

El dictamen de Gemini traía cuatro tareas. **Tres parten de premisas falsas**
y se verificaron contra el código antes de ejecutar nada.

### 3.1 — "Mantener la columna de estatus (Vigente, Suspendido, Revocado)"

**No existe.** El endpoint de precios de la CNE entrega
`<place place_id="…"><gas_price type="…">`, y el catálogo entrega permiso,
place_id, razón social, municipio, estado, región y coordenadas. **En ningún
punto del flujo hay un campo de estatus**, así que no hay nada que "mantener".

Además el dictamen pide hacerlo en `preparar_cliente.py`, que **no construye
el catálogo**: solo lo copia. Quien lo construye es `xml_a_csv.py`.

Se podría conseguir el estatus de otra fuente —el padrón de permisos de la
CNE es un conjunto distinto—, pero eso es integrar una fuente nueva, no
conservar una columna. Y hay que verificar antes si se publica de forma
legible por máquina.

### 3.2 — "Que el buscador acepte permiso CRE, municipio o marca"

**Ya lo hace**, menos la marca. El campo existe, con el texto de ayuda
*"Permiso CRE, razón social o municipio"*, con rebote de 180 ms.

Y **la marca no se puede buscar porque no existe**: está vacía en el 100% de
los registros, 0 de 96,969. Agregarla al buscador produciría un campo que
nunca encuentra nada.

### 3.3 — "Estructura 100% plana, sin la carpeta envolvente `v2/`"

**No hay carpeta `v2/`.** La raíz del repositorio solo tiene `clientes/`, que
es la multi-inquilino y debe quedarse.

### 3.4 — La vulnerabilidad que le atribuyen no es la que tienen

El dictamen afirma que Signal Fuels "usa la TAR pública para calcular
márgenes, dando cifras ficticias". **Su material no dice eso.** Dice
*"Compara el precio TAD, el de bomba y el de tu competencia en un mismo lugar
para decidir cuándo comprar y a cuánto vender"*. Eso es comparación, no
cálculo de margen.

Atacarlos por algo que no afirman es el camino más rápido a perder
credibilidad en una junta. **Su vulnerabilidad real es otra y está abajo.**

---

## 4. Los precios TAD: lo que sí averigüé

Esta era la pregunta de fondo, porque si los precios de terminal son públicos
y diarios, hay una brecha real. Lo que encontré:

**El conjunto abierto por terminal está vencido.** En datos.gob.mx el recurso
se titula literalmente *"Precios por terminal de almacenamiento y reparto de
gasolina regular, gasolina premium y diésel **(actualización a febrero de
2026)**"*. Ocho meses de retraso.

**El portal público de Pemex entrega un PDF, no datos.** El Portal de
Combustibles publica precios de venta de primera mano en PDF; la página
declara "Última actualización: mayo 2026" y remite al ejecutivo comercial
para históricos.

**Y el dato decisivo:** ese precio se publica **"antes de impuestos y
fletes"**, textual.

### Qué significa

**No pude verificar de ninguna fuente pública que exista un precio TAD diario
y por terminal.** Signal Fuels promete "Precios TAD actualizados cada día".
O tienen un acceso que no es público, o están modelando.

Y más importante: **aunque lo tuvieran, el precio TAD no es el costo del
gasolinero.** Le faltan el flete y el descuento negociado por contrato, que
es exactamente lo que dice la regla 1.4 de este proyecto. La fuente oficial
lo confirma con sus propias palabras: *antes de impuestos y fletes*.

**Ésa es su vulnerabilidad, y es la misma que la de fuelpricing:** venden el
insumo público de un costo y dejan que el cliente crea que es su costo.
`tar_referencia.PLANTILLA.csv` —donde el cliente captura su costo puesto en
estación, con vigencia de 30 días— ya resuelve lo que ellos no.

**El argumento para la junta:**

> "El precio de terminal se publica antes de impuestos y fletes. Lo dice
> Pemex. Quien te lo venda como tu costo te está vendiendo la mitad del
> número. Yo no te lo estimo: tú capturas tu costo puesto en estación, una
> vez, y a partir de ahí el punto de equilibrio es el tuyo."

---

## 5. Lo que sí se construyó: panel de cumplimiento del tope

En vez de las tres tareas del dictamen, se implementó la que sale de la
evidencia.

**El hallazgo.** El 19 de octubre, Expansión publicó un análisis de
PetroIntelligence con corte al 12 de octubre: *"86.5% comercializaba diésel a
un máximo de 27 pesos"*, es decir 13.5% de incumplimiento.

Tu padrón del 19 de octubre da **13.5% por encima de $27.00**. El mismo
número, calculado solo, contra la misma fuente pública.

Pero el compromiso de la Estrategia Nacional es un precio **menor a** $27.00,
no "a un máximo de". Y con esa distinción aparece lo que su análisis no
cuenta:

| Diésel, corte del 19 oct | |
|---|---|
| Cumple (por debajo de $27.00) | **42.3%** — 4,448 estaciones |
| **Exactamente en $27.00** | **44.2%** — 4,652 estaciones |
| Por encima de $27.00 | **13.5%** — 1,415 estaciones |

**El incumplimiento real es 57.7%, no 13.5%.** Casi la mitad del mercado del
diésel publica el tope exacto y cree que cumple.

En Regular: 82.4% cumple, 5.0% está justo en $24.00, 12.6% por encima →
17.6% de incumplimiento real.

El tablero ya clasificaba bien por estación (`excedeTope` usa `>=`, no `>`).
Lo que faltaba era el agregado. Ahora hay un panel de tres estados, no dos,
que se recalcula con el filtro activo y declara que es un pacto voluntario,
no una norma sancionable, y que la Zona Libre de la Frontera Norte produce
precios legítimamente menores.

---

## 6. Lo que NO se construyó, y por qué

**Indicadores macro (FIX, WTI/SPOT).** Signal Fuels los incluye y fuelpricing
los regala en su escalón gratuito. Replicarlos no diferencia: posiciona como
la versión barata de los dos. Y el dueño de una estación no fija precio con
el WTI: fija con su costo en terminal y con el de enfrente. `extraer_indicadores.py`
ya está escrito por si se quiere para instancias de comercializadora, donde sí
tiene sentido, detrás de una bandera apagada por omisión.

**Asistente de IA.** Es su único módulo que no se replica barato y es el que
más caro les sale. No hay que competir ahí todavía.
