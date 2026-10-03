# Monitor de Precios de Combustibles — LB GAS 23 · Servicio Bautista

Tablero web que convierte el padrón público de precios de la Comisión Nacional de
Energía en decisiones de precio para estaciones de servicio.

**Sitio publicado:** https://TU-USUARIO.github.io/TU-REPOSITORIO/
**Instancia de cliente:** `/clientes/enerso/`

---

## Estructura

```
index.html                   Tablero completo: CSS, librerías y aplicación embebidos
sw.js                        Service worker (VERSION lbgas23-v2)
manifest.json                Instalación como app en iOS y Android
favicon · apple-touch-icon · icono-192 · icono-512 · icono-512-maskable

fallback.csv                 Padrón con precios del último corte
historico.csv                Promedios diarios — MEMORIA LARGA, NO SE TOCA
historico.xlsx               El mismo histórico en Excel, lo descarga el botón
catalogo_estaciones.csv      place_id, permiso CRE, razón social, ubicación, coordenadas
reporte_mercado.csv          Métricas por marca y región con percentiles

xml_a_csv.py                 Conversor del XML oficial
preparar_cliente.py          Generador de instancias por cliente
historico_a_xlsx.py          Convierte el histórico a Excel

clientes/enerso/             Instancia lista para producción

.github/workflows/actualizar-datos.yml   Flujo diario automatizado
```

## Puesta en marcha

1. **Settings → Actions → General → Workflow permissions:** marca *Read and write permissions*.
2. **Settings → Pages → Deploy from a branch:** rama `main`, carpeta `/ (root)`.
3. **Actions → Actualizar precios de combustibles → Run workflow.**

El flujo corre solo todos los días a las 13:00 UTC (07:00 del centro de México) y los
lunes a las 14:00 UTC.

## Qué hace el flujo diario

1. Descarga el XML de la CNE y **valida que sea el padrón de precios**, no el catálogo.
2. Genera `fallback.csv`, acumula `historico.csv` y produce `reporte_mercado.csv`.
3. Convierte el histórico a `historico.xlsx`.
4. **Regenera `clientes/enerso/`** con el corte del día.
5. Publica todo en un solo commit.

Si el origen falla, la corrida termina en verde con un aviso y **no toca los datos
publicados**: el tablero sigue sirviendo el último corte bueno.

## Reglas que no se negocian

- **`historico.csv` es la memoria larga del proyecto.** Arranca el 19 de agosto de 2026.
  Nunca se borra, recorta ni reformatea.
- **La llave entre precios y catálogo es `place_id`**, no el permiso CRE.
- **Sin costo por litro no hay margen, hay ingreso**, y el tablero lo declara.
- Validar contenido, no solo códigos HTTP: un 200 puede traer el catálogo o un HTML de error.

## Generar una instancia de cliente

```bash
python3 preparar_cliente.py --origen . --salida clientes/<slug> \
        --slug <slug> --nombre "<Nombre comercial>" \
        --estado Jalisco --radio 5 --max-estaciones 10 \
        --centro "20.6736,-103.3440" --zoom 12 --xlsx historico.xlsx
```

`--max-estaciones` define el plan: 1 Estación · 5 Red · 15 Grupo.

## Regenerar el catálogo

```bash
curl -fsSL -o places.xml "https://publicacionexterna.azurewebsites.net/publicaciones/places"
python3 xml_a_csv.py places.xml --catalogo places.xml \
        --geojson entidades_mx.geojson --municipios municipios_mx.topojson \
        --exportar-catalogo catalogo_estaciones.csv --salida /dev/null
```

Los dos archivos de geometría no viven en el repositorio: se descargan solo para esto.
