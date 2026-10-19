# v14 · Ciberseguridad, estructura y cumplimiento legal

**Dos archivos: `index.html` y `sw.js`. Reemplazan los de la raíz del repo.**
Ningún CSV se toca. `historico.csv` y `movimientos.csv` son irrecuperables.

Service worker: `lbgas23-v9` → **`lbgas23-v10`**. Recarga dos veces al publicar.

---

## Lo que YA estaba bien, y no toqué

Audité antes de escribir. Cinco de las directrices ya estaban cumplidas, y
cambiarlas habría sido trabajo inventado:

| Directriz | Estado real |
|---|---|
| XSS en inyecciones al DOM | **0 de 37 `innerHTML` del código propio interpolan variables sin escapar.** Existe `esc()` y se usa |
| `eval`, `document.write`, `new Function` | **Cero ocurrencias** |
| Inyección por parámetros de URL | **No se leen:** cero `location.search`, cero `URLSearchParams` |
| Destrucción de gráficas | **Las 6 pasan por el helper `destroy(name)`** antes de redibujar. No hay fuga |
| Limpieza de capas del mapa | `clearLayers()` y `removeLayer` ya presentes |
| `console.log` de desarrollo | **Cero** en el código propio |

### Y una directriz que no aplica

Pediste declarar en el aviso de privacidad el *"cálculo de distancias por
geolocalización en tiempo real"*.

**El tablero no usa geolocalización.** Cero `navigator.geolocation`, cero
`map.locate()`. Las distancias se calculan con las coordenadas del catálogo
público de la CNE, no con la posición de quien consulta.

Escribir esa frase habría declarado un tratamiento de datos que no ocurre —un
aviso de privacidad que miente en contra tuya— así que el aviso dice lo
contrario: **que la ubicación no se solicita.** Eso es más fuerte ante un
cliente corporativo que la frase genérica.

---

## Lo que cambié

### 1. Política de Seguridad de Contenido

`<meta http-equiv="Content-Security-Policy">` con el conjunto cerrado de
orígenes que el tablero usa realmente, verificado contra el código:

```
default-src 'self'; script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' data: https://fonts.gstatic.com;
img-src 'self' data: blob: https://*.tile.openstreetmap.org;
connect-src 'self'; manifest-src 'self'; worker-src 'self';
object-src 'none'; base-uri 'self'; form-action 'none';
frame-ancestors 'none'; upgrade-insecure-requests
```

**Dos cosas que debes saber, y no son opcionales:**

`'unsafe-inline'` es inevitable. Toda la aplicación, el CSS y las tres
librerías van embebidos en el archivo para que abra como estático y el service
worker lo precargue completo. Quitarlo obliga a trocear el archivo, que es la
arquitectura que este producto deliberadamente no tiene. **Lo que sí se cierra
—y es lo que de verdad importa— son los orígenes externos:** sin CSP, un script
inyectado podía exfiltrar a cualquier dominio; ahora solo existen cuatro
destinos permitidos.

`frame-ancestors` **no surte efecto por meta.** Solo funciona como cabecera
HTTP, y GitHub Pages no permite definirlas. Lo dejé declarado para cuando
migres a un servidor o proxy propio, pero hoy la protección contra enmarcado
no está activa. El navegador lo reporta en consola; es esperado, no un error.

### 2. Service worker: coincidencia de host anclada

La regla de mosaicos era `/tile\.openstreetmap\.org/` sin anclar. Eso **también
casa con `tile.openstreetmap.org.dominio-ajeno.com`**: bastaba registrar ese
nombre para que el service worker cacheara contenido de un tercero como si
fuera del mapa.

Ahora es igualdad exacta o sufijo `.tile.openstreetmap.org`.

El resto del `fetch` ya validaba bien: filtra por protocolo `http`, y solo
guarda en caché cuando el origen es el propio. El cruzado nunca se cachea.

### 3. Aviso de Privacidad (LFPDPPP)

Modal accesible desde el pie, con el mismo patrón de los modales existentes
(`data-close`, cierre con Escape). Redactado contra lo que el tablero hace:

- **Responsable** e identidad comercial
- **Sitio estático:** sin servidor, sin base de usuarios, sin formularios
- **No se solicita la ubicación del dispositivo** (verificado en el código)
- **No se tratan datos sensibles**, ni cookies de rastreo o perfilado
- **Almacenamiento local:** qué guarda exactamente y cómo borrarlo
- **Derechos ARCO** a `lbgas23@gmail.com`

**Un apartado que no pediste y que agregué:** los dos terceros que reciben la
IP del visitante por el solo hecho de cargar la página — **Google Fonts** y los
**mosaicos de OpenStreetMap**. Una plantilla genérica lo omite; un comprador
corporativo que audite el sitio lo detecta en treinta segundos y te pregunta
por qué no estaba declarado.

### 4. Consentimiento de almacenamiento local

Banner flotante, no intrusivo, con "Entendido" y acceso directo al aviso. La
bandera se guarda en `localStorage` **entre `try/catch`**: en modo privado
estricto lanza excepción, y sin la guarda el banner tumbaría la página justo en
el navegador más restrictivo. Si no se puede leer el consentimiento, el aviso
se muestra: fallar hacia mostrarlo molesta una vez más, pero nunca omite el
aviso a quien no lo ha visto.

El bloque de JavaScript es **autocontenido**, fuera del IIFE principal: si algo
falla ahí, no puede romper el tablero.

### 5. Deslinde legal

En el pie y dentro del simulador. El del simulador es más directo porque es
donde se toma la decisión:

> *Escenario matemático, no asesoría financiera. Sin tu costo por litro esto es
> diferencial contra el mercado, no utilidad. El resultado no garantiza
> rendimientos: depende de variables que esta plataforma no observa, empezando
> por tu volumen real.*

---

## Verificado en navegador, no sobre el papel

Servido local con los datos reales del repositorio y abierto en Chromium:

- **Cero errores de JavaScript**
- **Cero bloqueos de CSP** salvo el aviso esperado de `frame-ancestors`
- Modal abre desde el pie, cierra con el botón y con Escape
- Banner aparece, se oculta al aceptar y **sigue oculto tras recargar**
- Deslindes presentes en pie y simulador

**Un defecto que encontré en mi propio parche y corregí:** el banner no se
ocultaba. `.consent{display:flex}` le gana por especificidad a
`[hidden]{display:none}`, así que el atributo no hacía nada y el aviso quedaba
visible para siempre aunque se aceptara. Agregada la regla `.consent[hidden]`.
El código ya tenía ese patrón en `.modal`, `.empty` y `.sw-aviso`; mi omisión
era la anomalía.

---

## Lo que queda pendiente y no depende de mí

- **`frame-ancestors` real:** requiere cabecera HTTP. GitHub Pages no las
  permite. Si llega un cliente que lo exija en una auditoría, es motivo para
  mover el alojamiento, no para tocar el código.
- **Píxel de Meta y medio de contacto en la página:** siguen sin instalarse.
  Necesito tu Pixel ID.
