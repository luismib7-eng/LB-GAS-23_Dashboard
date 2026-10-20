#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auditoria.py — LB GAS 23 · Auditoría estricta del repositorio publicado

POR QUE EXISTE ESTE ARCHIVO
---------------------------
El 20 de octubre de 2026 se descubrió que la corrección del error 15 llevaba
semanas ausente del `index.html` publicado. Estaba documentada en el registro
de errores y borrada del código: una entrega completa la había regresado a un
estado anterior y nadie lo verificó. El sitio mostraba 266 competidores donde
hay 38.

Ningún error de este proyecto se ha detectado solo. Todos los encontró alguien
mirando. Este script es ese alguien, todas las semanas.

QUE AUDITA, Y POR QUE ASI
-------------------------
El bloque más importante es el CENTINELA DE REGRESIONES: una lista de marcas
de código que DEBEN existir y de patrones que NO deben existir, cada una atada
al número de error que la originó. Si una corrección se pierde otra vez, la
auditoría lo dice el lunes siguiente y no en una captura de pantalla de un
cliente.

SEVERIDADES
-----------
  CRITICO  rompe el producto o publica un dato falso. Sale con código 1.
  ALERTA   hay que revisarlo esta semana.
  AVISO    contexto que conviene saber.

Uso:
    python3 auditoria.py [ruta_del_repo]        # por omisión, el directorio actual
    python3 auditoria.py --markdown             # salida para pegar en un reporte
"""
import csv
import collections
import datetime
import io
import json
import os
import re
import subprocess
import sys

HOY = datetime.date.today()
SERIE_ARRANCA = "2026-08-19"      # regla 1.2: irrecuperable
BITACORA_ARRANCA = "2026-10-01"

CRITICO, ALERTA, AVISO, BIEN = "CRITICO", "ALERTA", "AVISO", "BIEN"

# ─────────────────────────────────────────────────────────────────────
#  CENTINELA DE REGRESIONES
#
#  Cada entrada ata una corrección del registro de errores a una marca
#  verificable en el código. Si la marca desaparece, la corrección se
#  perdió. Esto es lo que no existía cuando el error 15 volvió.
# ─────────────────────────────────────────────────────────────────────
DEBE_EXISTIR = [
    # (archivo, marca, error, qué protege)
    ("index.html", "function unicas(", 18,
     "colapsar registros a una fila por estación"),
    ("index.html", "var est = unicas(rows)", 18,
     "render() separa registros de estaciones"),
    ("index.html", "unicas(rows).filter", 18,
     "la rejilla espacial se indexa con estaciones únicas"),
    ("index.html", "function acumularGrupo(", 17,
     "el panel de operador cuenta permisos distintos, no registros"),
    ("index.html", "sitiosN", 17,
     "conteo de estaciones distintas por grupo operador"),
    ("index.html", "function permitKey(", 4,
     "normalización de los dos formatos de permiso"),
    ("index.html", "function esc(", 0,
     "escapado de HTML contra XSS"),
    ("index.html", "paresValidos", 15,
     "la dinámica descarta pares de cortes no consecutivos"),
    ("index.html", "diasEntreCortes", 15,
     "criterio de días consecutivos"),
    ("index.html", "Content-Security-Policy", 0,
     "política de seguridad de contenido"),
    ("index.html", "avisoModal", 0,
     "aviso de privacidad LFPDPPP"),
    ("index.html", ".consent[hidden]", 0,
     "la regla que permite ocultar el banner de consentimiento"),
    ("index.html", "function topeEstrategia(", 0,
     "tope del pacto SENER"),
    ("index.html", "precio >= t.valor", 0,
     "el precio EXACTAMENTE en el tope no cumple (pacto dice 'menor a')"),
    ("index.html", "function bandaTamano(", 0,
     "índice de tamaño del DENUE"),
    ("xml_a_csv.py", "_conservar_sin_borrar", 13,
     "el histórico y la bitácora nunca se recortan"),
    ("preparar_cliente.py", "limites_app_config", 16,
     "delimitar APP_CONFIG contando llaves, no por el literal '};'"),
    ("sw.js", "openstreetmap\\.org$", 0,
     "coincidencia de host anclada en el service worker"),
]

NO_DEBE_EXISTIR = [
    ("index.html", "fuente[k].length", 17,
     "contaba registros y los rotulaba estaciones"),
    ("index.html", "n: fuente[k].length", 17,
     "idem"),
    ("xml_a_csv.py", "default=120", 13,
     "recorte del histórico: borraba la serie"),
    ("xml_a_csv.py", "conservar=400", 13,
     "recorte de la bitácora"),
    (".github/workflows/actualizar-datos.yml", "historico-conservar 120", 13,
     "recorte del histórico en el flujo diario"),
    (".github/workflows/actualizar-datos.yml", "movimientos-conservar 400", 13,
     "recorte de la bitácora en el flujo diario"),
    ("index.html", "document.write", 0, "vector de inyección"),
    ("index.html", "eval(", 0, "vector de inyección"),
]


class Reporte(object):
    def __init__(self):
        self.items = []

    def add(self, sev, bloque, titulo, detalle="", err=None):
        self.items.append({"sev": sev, "bloque": bloque, "titulo": titulo,
                           "detalle": detalle, "err": err})

    def por_sev(self, sev):
        return [i for i in self.items if i["sev"] == sev]

    def falla(self):
        return bool(self.por_sev(CRITICO))


def leer(ruta):
    try:
        with io.open(ruta, encoding="utf-8-sig", newline="") as h:
            return h.read()
    except Exception:
        return None


def filas(ruta):
    t = leer(ruta)
    if t is None:
        return None
    return list(csv.DictReader(io.StringIO(t)))


def dia(s):
    a, b, c = s.split("-")
    return datetime.date(int(a), int(b), int(c))


# ─────────────────────────────────────────────────────────────────────
def bloque_estructura(raiz, R):
    """Error 2: el árbol del commit debe ser plano en la raíz."""
    for f in ("index.html", "sw.js", "manifest.json", ".nojekyll",
              "xml_a_csv.py", "preparar_cliente.py"):
        if not os.path.exists(os.path.join(raiz, f)):
            R.add(CRITICO, "Estructura", "Falta %s en la raíz" % f,
                  "GitHub Pages publica desde la raíz; sin este archivo el sitio "
                  "no funciona.", 2)
    wf = os.path.join(raiz, ".github", "workflows", "actualizar-datos.yml")
    if not os.path.exists(wf):
        R.add(CRITICO, "Estructura", "Falta el workflow diario",
              "Sin él no hay corte y la serie deja de acumular.", 2)
    # Carpeta envolvente: un directorio que contenga otro index.html
    for d in os.listdir(raiz):
        p = os.path.join(raiz, d)
        if d in (".git", "clientes", ".github"):
            continue
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "index.html")):
            R.add(ALERTA, "Estructura", "Carpeta envolvente sospechosa: %s/" % d,
                  "El error 2 fue exactamente esto.", 2)
    if not R.por_sev(CRITICO):
        R.add(BIEN, "Estructura", "Árbol plano en la raíz, con workflow")


def bloque_centinela(raiz, R):
    """Error 18: verificar que las correcciones del registro sigan en el código."""
    cache = {}

    def texto(rel):
        if rel not in cache:
            cache[rel] = leer(os.path.join(raiz, rel)) or ""
        return cache[rel]

    perdidas = 0
    for rel, marca, err, protege in DEBE_EXISTIR:
        t = texto(rel)
        if not t:
            R.add(CRITICO, "Centinela", "No se pudo leer %s" % rel, "", err)
            perdidas += 1
            continue
        if marca not in t:
            R.add(CRITICO, "Centinela",
                  "CORRECCIÓN PERDIDA en %s" % rel,
                  "Falta «%s». Protegía: %s. Es el mecanismo del error 18: una "
                  "entrega completa regresó el archivo a un estado anterior."
                  % (marca, protege), err)
            perdidas += 1
    for rel, marca, err, porque in NO_DEBE_EXISTIR:
        t = texto(rel)
        if t and marca in t:
            R.add(CRITICO, "Centinela",
                  "PATRÓN PROHIBIDO reapareció en %s" % rel,
                  "Encontrado «%s». %s" % (marca, porque), err)
            perdidas += 1
    if not perdidas:
        R.add(BIEN, "Centinela",
              "Las %d correcciones del registro siguen en el código"
              % len(DEBE_EXISTIR),
              "y ninguno de los %d patrones prohibidos reapareció."
              % len(NO_DEBE_EXISTIR))


def bloque_series(raiz, R):
    """Regla 1.2 y error 13: las series acumuladas son irrecuperables."""
    h = filas(os.path.join(raiz, "historico.csv"))
    if h is None:
        R.add(CRITICO, "Series", "No se pudo leer historico.csv",
              "Es la memoria larga del proyecto.", 13)
    else:
        f = sorted({r["Fecha"] for r in h})
        if not f:
            R.add(CRITICO, "Series", "historico.csv sin fechas", "", 13)
        else:
            if f[0] != SERIE_ARRANCA:
                R.add(CRITICO, "Series",
                      "El histórico YA NO arranca el %s" % SERIE_ARRANCA,
                      "Arranca el %s. Se perdieron días irrecuperables: la CNE no "
                      "republica series. Restaurar desde el historial de commits."
                      % f[0], 13)
            hue = [(f[i-1], f[i]) for i in range(1, len(f))
                   if (dia(f[i]) - dia(f[i-1])).days != 1]
            if hue:
                R.add(ALERTA, "Series",
                      "%d hueco(s) en el histórico" % len(hue),
                      "; ".join("%s → %s" % x for x in hue[:6]), 13)
            atraso = (HOY - dia(f[-1])).days
            if atraso > 2:
                R.add(CRITICO, "Series",
                      "El histórico lleva %d días sin actualizarse" % atraso,
                      "Última fecha %s. Revisa GitHub Actions." % f[-1], 3)
            if not hue and f[0] == SERIE_ARRANCA and atraso <= 2:
                R.add(BIEN, "Series",
                      "Histórico completo: %d fechas, %s → %s, sin huecos"
                      % (len(f), f[0], f[-1]))

    m = filas(os.path.join(raiz, "movimientos.csv"))
    if m is None:
        R.add(ALERTA, "Series", "No se pudo leer movimientos.csv", "", 13)
    else:
        f = sorted({r["Fecha"] for r in m})
        if f and f[0] != BITACORA_ARRANCA:
            R.add(CRITICO, "Series",
                  "La bitácora YA NO arranca el %s" % BITACORA_ARRANCA,
                  "Arranca el %s." % f[0], 13)
        elif f:
            falt = []
            cur = dia(f[0])
            while cur <= dia(f[-1]):
                if cur.isoformat() not in f:
                    falt.append(cur.isoformat())
                cur = datetime.date.fromordinal(cur.toordinal() + 1)
            R.add(AVISO if falt else BIEN, "Series",
                  "Bitácora: %d fechas, %s → %s" % (len(f), f[0], f[-1]),
                  ("Días sin registro: " + ", ".join(falt)) if falt else "")
        # Horizonte de tamaño: GitHub rechaza archivos de más de 100 MB
        mb = os.path.getsize(os.path.join(raiz, "movimientos.csv")) / 1048576.0
        if mb > 60:
            R.add(ALERTA, "Series",
                  "movimientos.csv pesa %.1f MB" % mb,
                  "GitHub rechaza archivos de más de 100 MB. Toca archivar por año.")


def bloque_padron(raiz, R):
    """Salud del corte del día y de las cifras que el tablero publica."""
    fb = filas(os.path.join(raiz, "fallback.csv"))
    if fb is None:
        R.add(CRITICO, "Padrón", "No se pudo leer fallback.csv", "", 1)
        return
    cortes = sorted({r["Fecha"] for r in fb})
    ult = cortes[-1] if cortes else None
    if not ult:
        R.add(CRITICO, "Padrón", "fallback.csv sin fechas", "", 1)
        return
    atraso = (HOY - dia(ult)).days
    if atraso > 2:
        R.add(CRITICO, "Padrón", "El corte lleva %d días sin publicar" % atraso,
              "Último: %s. Revisa que el workflow no esté fallando." % ult, 3)
    noconsec = [(cortes[i-1], cortes[i]) for i in range(1, len(cortes))
                if (dia(cortes[i]) - dia(cortes[i-1])).days != 1]
    if noconsec:
        R.add(ALERTA, "Padrón",
              "La ventana tiene cortes no consecutivos",
              "; ".join("%s → %s" % x for x in noconsec) +
              ". La dinámica y la conducta descartan esos pares, pero conviene "
              "saber por qué faltó el día.", 15)

    U = [r for r in fb if r["Fecha"] == ult]
    est = len({r["Permiso CRE"] for r in U})
    R.add(BIEN, "Padrón",
          "Corte %s · %s estaciones · %d cortes · %s registros"
          % (ult, "{:,}".format(est), len(cortes), "{:,}".format(len(fb))))

    # Error 4: si la marca deja de estar vacía, es noticia y cambia el producto
    conmarca = sum(1 for r in fb if (r.get("Marca") or "").strip())
    if conmarca:
        R.add(AVISO, "Padrón",
              "La columna Marca YA NO está vacía: %d de %d registros"
              % (conmarca, len(fb)),
              "Si la CNE empezó a publicar bandera, se puede reactivar el "
              "análisis por marca. Verificar antes de prometerlo.", 4)

    # Error 1: huella estadística contra datos sintéticos
    dec = collections.Counter()
    vals = []
    for r in U:
        v = (r.get("Regular") or "").strip()
        if not v:
            continue
        try:
            x = float(v)
        except ValueError:
            continue
        vals.append(x)
        dec[int(round(x * 100)) % 100] += 1
    if vals:
        top = sum(c for d, c in dec.items() if d in (99, 0, 49, 50, 89, 90, 95, 9, 19, 29))
        pct = 100.0 * top / len(vals)
        distintos = len(dec)
        # El disparador es SOLO la concentración. Con casi 14,000 estaciones
        # es normal que aparezcan 99 de los 100 decimales posibles; lo que
        # delata un archivo generado al azar es que los precios NO se amontonen
        # en .99, .49 y .00. Una primera versión de esta auditoría alertaba por
        # la variedad y marcaba como sintético el padrón real: una auditoría
        # que grita lobo se deja de leer, que es peor que no tenerla.
        if pct < 25:
            R.add(CRITICO, "Padrón",
                  "fallback.csv parece sintético",
                  "Solo %.1f%% de los precios terminan en valores comerciales y hay "
                  "%d decimales distintos. Los precios reales se amontonan en .99, "
                  ".49 y .00. Es la huella del error 1." % (pct, distintos), 1)
        else:
            R.add(BIEN, "Padrón",
                  "Huella de precios reales: %.1f%% en terminaciones comerciales, "
                  "%d decimales distintos" % (pct, distintos))
        mn, mx = min(vals), max(vals)
        if mn < 15.0:
            R.add(ALERTA, "Padrón", "Precio bajo el piso de depuración: $%.2f" % mn,
                  "El filtro descarta bajo $15.00. Si la franja fronteriza bajó por "
                  "política fiscal, hay que revisar el umbral antes de culpar a la fuente.")
        R.add(AVISO, "Padrón", "Regular del corte: $%.2f – $%.2f" % (mn, mx))

    # Cruce con el catálogo (regla 1.3: la llave es place_id)
    cat = filas(os.path.join(raiz, "catalogo_estaciones.csv"))
    if cat:
        pid = [r.get("Place ID") for r in cat]
        if len(set(pid)) != len(pid):
            R.add(ALERTA, "Padrón", "Place ID duplicados en el catálogo",
                  "%d filas, %d place_id únicos" % (len(pid), len(set(pid))), 3)
        fuera = 0
        for r in cat:
            try:
                la, lo = float(r["Lat"]), float(r["Lon"])
            except (TypeError, ValueError):
                continue
            if not (14.0 <= la <= 33.0 and -118.5 <= lo <= -86.0):
                fuera += 1
        # El error 10 dejó 85 estaciones en (0,0): condición conocida y
        # manejada por la caja envolvente. Solo interesa si CAMBIA.
        BASE_FUERA = 85
        if fuera > BASE_FUERA * 1.3:
            R.add(ALERTA, "Padrón",
                  "Subieron las coordenadas fuera de México: %d (antes ~%d)"
                  % (fuera, BASE_FUERA),
                  "El tablero las anula, pero un salto sugiere que la fuente cambió.", 10)
        elif fuera:
            R.add(AVISO, "Padrón",
                  "%d coordenadas fuera de la caja de México, dentro de lo esperado"
                  % fuera, "", 10)


def bloque_codigo(raiz, R):
    """Errores 9 y 17: llamadas huérfanas y documentación a la deriva."""
    t = leer(os.path.join(raiz, "index.html"))
    if not t:
        return
    bloques = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", t, re.S)
    # Solo el bloque de la aplicación. Leaflet, Chart.js y PapaParse van
    # embebidos en sus propios <script> y sus métodos internos (_drawDataset,
    # _computeLabelItems…) aparecían como 434 llamadas huérfanas. Ese ruido
    # es la forma en que un reporte semanal se vuelve inútil.
    propios = [b for b in bloques if "renderCompetencia" in b or "function render()" in b]
    js = "\n".join(propios) if propios else ""
    if not js:
        R.add(ALERTA, "Código", "No se encontró el bloque de la aplicación",
              "La auditoría de llamadas huérfanas no pudo correr.", 9)
        return

    definidas = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", js))
    definidas |= set(re.findall(r"(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*function", js))
    definidas |= set(re.findall(r"(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*\(", js))
    llamadas = set(re.findall(r"(?<![\w.$])([a-z_$][\w$]{3,})\s*\(", js))
    nativas = set("""if for while switch catch return typeof function new delete void
        parseInt parseFloat isNaN isFinite decodeURI encodeURI setTimeout setInterval
        clearTimeout clearInterval require import fetch alert confirm prompt Number
        String Boolean Array Object Promise Date Math JSON console document window
        localStorage sessionStorage navigator location history addEventListener
        removeEventListener querySelector querySelectorAll getElementById forEach
        toLocaleString toFixed charCodeAt indexOf lastIndexOf includes startsWith
        endsWith replace split join slice splice concat filter reduce some every
        sort reverse push pop shift unshift keys values entries assign create
        hasOwnProperty toString valueOf bind call apply catch then finally resolve
        reject all race map set get has add clear delete size trim toUpperCase
        toLowerCase padStart padEnd repeat match matchAll search test exec
        getAttribute setAttribute removeAttribute appendChild removeChild
        createElement createTextNode insertBefore cloneNode contains closest
        preventDefault stopPropagation requestAnimationFrame
        cancelAnimationFrame getComputedStyle scrollIntoView focus blur
        normalize from isArray stringify parse floor ceil round abs min max pow
        sqrt random sign log exp cos sin atan2 asin acos""".split())
    huerfanas = sorted(c for c in llamadas - definidas - nativas
                       if not c.startswith("_"))
    # Solo las que de verdad parecen del proyecto: se usan y no se definen
    sospechosas = [c for c in huerfanas
                   if re.search(r"(?<![\w.$])%s\s*\(" % re.escape(c), js)
                   and c not in ("constructor", "super")]
    if len(sospechosas) > 25:
        R.add(AVISO, "Código",
              "%d identificadores llamados sin definición local" % len(sospechosas),
              "Casi todos son métodos de librería. Revisión manual si crece de golpe.", 9)
    else:
        for c in sospechosas[:10]:
            R.add(ALERTA, "Código", "Posible llamada huérfana: %s()" % c,
                  "Confirma que exista o que venga de Leaflet/Chart.js/PapaParse.", 9)
        if not sospechosas:
            R.add(BIEN, "Código", "Sin llamadas huérfanas detectadas")

    # Error 17: el README no debe describir una arquitectura muerta
    # El README puede nombrar la arquitectura vieja PARA DECIR que ya no existe
    # («No hay styles.css, app.js ni config.js: se consolidaron aquí»). Esa
    # mención es correcta y no debe alertar: una auditoría que castiga la
    # documentación honesta empuja a borrarla. Solo cuenta la mención que
    # presenta lo viejo como vigente.
    rd = leer(os.path.join(raiz, "README.md")) or ""
    NIEGA = ("no hay", "ya no", "retirad", "retiró", "se eliminó", "histórico",
             "vencid", "anterior", "consolidaron", "dejó de", "(retirada)",
             "no se usa", "nota de revisión")
    MUERTO = ("app.js", "styles.css", "config.js", "Apps Script",
              "Google Sheets", "inferirUbicacion", "MARCAS_COMPETENCIA")

    # La revisión es CONSCIENTE DE SECCIONES: un encabezado marcado como
    # histórico o retirado exime a todo su cuerpo hasta el siguiente
    # encabezado del mismo nivel o superior. Documentar lo que se retiró es
    # correcto y útil; lo que no se vale es presentarlo como vigente.
    muertos = []
    exenta_hasta = 0          # nivel de encabezado que abrió la exención
    for i, ln in enumerate(rd.split("\n"), 1):
        bajo = ln.lower()
        enc = re.match(r"(#{1,6})\s", ln)
        if enc:
            nivel = len(enc.group(1))
            if any(x in bajo for x in NIEGA):
                exenta_hasta = nivel          # abre sección histórica
            elif exenta_hasta and nivel <= exenta_hasta:
                exenta_hasta = 0              # la cierra
        if exenta_hasta:
            continue
        if any(x in bajo for x in NIEGA):
            continue
        for m in MUERTO:
            if m in ln:
                muertos.append("%s (línea %d)" % (m, i))
    if muertos:
        R.add(ALERTA, "Código", "El README describe arquitectura que ya no existe",
              "Presenta como vigente: " + ", ".join(muertos[:6]) +
              ". Dos auditorías externas ya reportaron defectos inexistentes por esto.", 17)

    R.add(AVISO, "Código", "index.html pesa %.0f KB"
          % (os.path.getsize(os.path.join(raiz, "index.html")) / 1024.0),
          "Es una PWA que debe abrir como archivo estático; vigila que no crezca sin razón.")


def bloque_clientes(raiz, R):
    """Error 16: las instancias no deben quedar con el bloque duplicado."""
    base = os.path.join(raiz, "clientes")
    if not os.path.isdir(base):
        R.add(AVISO, "Clientes", "No hay carpeta clientes/")
        return
    n = 0
    for dirpath, _dirnames, filenames in os.walk(base):
        if "index.html" not in filenames:
            continue
        n += 1
        t = leer(os.path.join(dirpath, "index.html")) or ""
        rel = os.path.relpath(dirpath, raiz)
        if t.count('<script id="app"') != 1:
            R.add(CRITICO, "Clientes",
                  "%s tiene %d bloques <script id=\"app\">" % (rel, t.count('<script id="app"')),
                  "La página queda rota. Es el error 16.", 16)
        if t.count("window.APP_CONFIG =") != 1:
            R.add(CRITICO, "Clientes",
                  "%s tiene %d definiciones de window.APP_CONFIG"
                  % (rel, t.count("window.APP_CONFIG =")), "", 16)
        if "function unicas(" not in t:
            R.add(AVISO, "Clientes",
                  "%s trae código anterior al último cambio" % rel,
                  "El paso «Regenerar las instancias» del flujo diario lo propaga "
                  "en el próximo corte. Solo es ALERTA si sigue igual pasados dos "
                  "días: ahí el paso está fallando.", 18)
    R.add(BIEN if n else AVISO, "Clientes", "%d instancia(s) revisada(s)" % n)


def bloque_flujo(raiz, R):
    """Que el flujo diario no recorte nada y commitee lo que genera."""
    wf = leer(os.path.join(raiz, ".github", "workflows", "actualizar-datos.yml")) or ""
    if not wf:
        return
    for arg, err in (("--historico-conservar 0", 13), ("--movimientos-conservar 0", 13)):
        if arg not in wf:
            R.add(CRITICO, "Flujo", "El workflow NO pasa %s" % arg,
                  "Sin esto el corte diario recorta una serie irrecuperable.", err)
    # Todo archivo que el ETL genera debe estar en el git add
    gen = re.findall(r"--(?:conducta|reporte|historico|movimientos)\s+([\w.]+\.csv)", wf)
    m = re.search(r"git add ([^\n]+)", wf)
    agregados = m.group(1) if m else ""
    for g in set(gen):
        if g not in agregados:
            R.add(CRITICO, "Flujo", "%s se genera pero no se commitea" % g,
                  "El `git add` del workflow no lo incluye: el archivo se "
                  "regenera cada día y nunca llega al sitio.", 2)
    if "--conservar 7" not in wf:
        R.add(AVISO, "Flujo", "La ventana del padrón no es de 7 cortes",
              "Si cambió, las cifras de la base de conocimiento quedan vencidas.")


def bloque_git(raiz, R):
    """Última corrida y ritmo de publicación."""
    try:
        out = subprocess.check_output(
            ["git", "-C", raiz, "log", "-1", "--format=%ad|%s", "--date=iso"],
            stderr=subprocess.DEVNULL).decode("utf-8", "replace").strip()
        fecha, msg = out.split("|", 1)
        R.add(BIEN, "Repositorio", "Último commit: %s" % msg.strip(),
              fecha.strip())
    except Exception:
        R.add(AVISO, "Repositorio", "Sin historial git disponible",
              "La auditoría corrió sobre una copia sin .git")


# ─────────────────────────────────────────────────────────────────────
#  SINTAXIS — que todo lo que se publica al menos COMPILE
#
#  La auditoría anterior verificaba que los parches existieran pero nunca
#  comprobaba que el código corriera. Un `index.html` con un error de
#  sintaxis pasa todos los centinelas y deja el sitio en blanco.
# ─────────────────────────────────────────────────────────────────────
def _hay(cmd):
    try:
        subprocess.check_output([cmd, "--version"], stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def bloque_sintaxis(raiz, R):
    import tempfile
    # --- Python: TODOS los .py del repositorio, no solo los que se tocan ---
    pys = sorted(f for f in os.listdir(raiz) if f.endswith(".py"))
    malos = []
    for f in pys:
        r = subprocess.run([sys.executable, "-I", "-m", "py_compile",
                            os.path.join(raiz, f)],
                           capture_output=True)
        if r.returncode:
            malos.append((f, r.stderr.decode("utf-8", "replace")[-200:]))
    for f, e in malos:
        R.add(CRITICO, "Sintaxis", "%s no compila" % f, e)
    if pys and not malos:
        R.add(BIEN, "Sintaxis", "Los %d scripts de Python compilan" % len(pys),
              ", ".join(pys))

    # --- YAML del workflow ---
    wf = os.path.join(raiz, ".github", "workflows", "actualizar-datos.yml")
    if os.path.exists(wf):
        try:
            import yaml
            with io.open(wf, encoding="utf-8") as h:
                d = yaml.safe_load(h)
            pasos = list(d["jobs"].values())[0]["steps"]
            R.add(BIEN, "Sintaxis", "El workflow es YAML válido",
                  "%d pasos" % len(pasos))
        except ImportError:
            R.add(AVISO, "Sintaxis", "Sin PyYAML: no se validó el workflow")
        except Exception as e:
            R.add(CRITICO, "Sintaxis", "El workflow no es YAML válido",
                  str(e)[:200], 2)

    # --- manifest.json ---
    mf = os.path.join(raiz, "manifest.json")
    if os.path.exists(mf):
        try:
            with io.open(mf, encoding="utf-8") as h:
                man = json.load(h)
            faltan = [i.get("src") for i in man.get("icons", [])
                      if i.get("src") and not os.path.exists(os.path.join(raiz, i["src"]))]
            if faltan:
                R.add(ALERTA, "Sintaxis", "El manifest declara iconos que no existen",
                      ", ".join(str(x) for x in faltan), 7)
            else:
                R.add(BIEN, "Sintaxis", "manifest.json válido, con sus iconos")
        except Exception as e:
            R.add(CRITICO, "Sintaxis", "manifest.json inválido", str(e)[:160], 7)

    # --- JavaScript: index.html raíz y cada instancia de cliente ---
    if not _hay("node"):
        R.add(AVISO, "Sintaxis", "Sin node: no se validó el JavaScript",
              "En el runner de Actions node sí está; en otros entornos puede faltar.")
        return
    objetivos = [("index.html", os.path.join(raiz, "index.html"))]
    base = os.path.join(raiz, "clientes")
    if os.path.isdir(base):
        for dp, _dn, fn in os.walk(base):
            if "index.html" in fn:
                objetivos.append((os.path.relpath(dp, raiz),
                                  os.path.join(dp, "index.html")))
    fallos = 0
    tmp = tempfile.mkdtemp(prefix="aud-js-")
    for etq, ruta in objetivos:
        t = leer(ruta)
        if not t:
            continue
        bloques = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", t, re.S)
        for k, b in enumerate(bloques):
            f = os.path.join(tmp, "b%d.js" % k)
            with io.open(f, "w", encoding="utf-8") as h:
                h.write(b)
            r = subprocess.run(["node", "--check", f], capture_output=True)
            if r.returncode:
                fallos += 1
                R.add(CRITICO, "Sintaxis",
                      "JavaScript inválido en %s (bloque %d de %d)"
                      % (etq, k + 1, len(bloques)),
                      r.stderr.decode("utf-8", "replace")[:220])
    if not fallos:
        R.add(BIEN, "Sintaxis",
              "JavaScript válido en %d página(s)" % len(objetivos))


# ─────────────────────────────────────────────────────────────────────
#  REFERENCIAS — que no haya 404 esperando al primer visitante
# ─────────────────────────────────────────────────────────────────────
def bloque_referencias(raiz, R):
    t = leer(os.path.join(raiz, "index.html")) or ""
    faltan = []
    # Archivos de datos declarados en la configuración
    for m in re.finditer(r'([A-Z_]+_CSV|HISTORY_CSV|XLSX\w*)\s*:\s*"([^"]+)"', t):
        ref = m.group(2).strip()
        if not ref or ref.startswith("http"):
            continue
        if not os.path.exists(os.path.join(raiz, ref)):
            faltan.append((m.group(1), ref))
    for llave, ref in faltan:
        R.add(CRITICO, "Referencias", "%s apunta a un archivo que no existe" % llave,
              "«%s». El tablero pedirá un 404 en cada carga." % ref, 11)

    # Precarga del service worker: todo lo que lista debe existir
    sw = leer(os.path.join(raiz, "sw.js")) or ""
    m = re.search(r"(?:CASCARON|SHELL|PRECACHE|ARCHIVOS)\s*=\s*\[(.*?)\]", sw, re.S)
    if m:
        refs = re.findall(r'"([^"]+)"', m.group(1))
        perdidos = [r_ for r_ in refs
                    if not r_.startswith("http") and r_ not in ("./", "/", "")
                    and not os.path.exists(os.path.join(raiz, r_.lstrip("./")))]
        if perdidos:
            R.add(CRITICO, "Referencias",
                  "El service worker precarga archivos que no existen",
                  ", ".join(perdidos) + ". La instalación del worker falla entera "
                  "si un archivo del cascarón da 404.", 11)
        else:
            R.add(BIEN, "Referencias",
                  "Los %d archivos del cascarón del service worker existen" % len(refs))
    if not faltan:
        R.add(BIEN, "Referencias", "Sin referencias rotas en la configuración")


# ─────────────────────────────────────────────────────────────────────
#  COHERENCIA ENTRE ARCHIVOS
#
#  Cada CSV por separado puede estar bien y el conjunto estar mal: que la
#  conducta hable de permisos que el catálogo no conoce, o que el reporte
#  de mercado tenga menos fechas que el histórico.
# ─────────────────────────────────────────────────────────────────────
def bloque_coherencia(raiz, R):
    cat = filas(os.path.join(raiz, "catalogo_estaciones.csv"))
    if not cat:
        return
    permisos = {(r.get("Permiso CRE") or "").strip() for r in cat}

    cd = filas(os.path.join(raiz, "conducta.csv"))
    if cd is not None:
        huerf = [r["Permiso CRE"] for r in cd
                 if (r.get("Permiso CRE") or "").strip() not in permisos]
        if huerf:
            R.add(ALERTA, "Coherencia",
                  "conducta.csv tiene %d permisos que el catálogo no conoce" % len(huerf),
                  "Ejemplos: " + ", ".join(huerf[:3]) +
                  ". El panel de conducta no los va a poder cruzar.")
        else:
            R.add(BIEN, "Coherencia",
                  "conducta.csv: los %d permisos existen en el catálogo" % len(cd))

    h = filas(os.path.join(raiz, "historico.csv"))
    rm = filas(os.path.join(raiz, "reporte_mercado.csv"))
    if h and rm:
        fh = {r["Fecha"] for r in h}
        fr = {r["Fecha"] for r in rm}
        falt = sorted(fh - fr)
        if falt:
            R.add(ALERTA, "Coherencia",
                  "reporte_mercado.csv tiene %d fechas menos que el histórico" % len(falt),
                  "Faltan: " + ", ".join(falt[:5]) +
                  ". Los dos los escribe el mismo corte: si uno se quedó atrás, "
                  "una corrida falló a medias.", 13)
        else:
            R.add(BIEN, "Coherencia",
                  "Histórico y reporte de mercado comparten las %d fechas" % len(fh))
        # Los percentiles ya deben venir en el reporte
        if rm and "P25" not in rm[0]:
            R.add(ALERTA, "Coherencia",
                  "reporte_mercado.csv no trae las columnas de percentiles",
                  "El ETL vigente las escribe; si faltan, el archivo es de una "
                  "versión anterior.")

    fb = filas(os.path.join(raiz, "fallback.csv"))
    if fb and permisos:
        ult = max(r["Fecha"] for r in fb)
        U = [r for r in fb if r["Fecha"] == ult]
        sin = [r["Permiso CRE"] for r in U
               if (r.get("Permiso CRE") or "").strip() not in permisos]
        pct = 100.0 * len(sin) / len(U) if U else 0
        if pct > 1.0:
            R.add(ALERTA, "Coherencia",
                  "%d de %d registros del corte no cruzan con el catálogo (%.2f%%)"
                  % (len(sin), len(U), pct),
                  "Históricamente son ~5 con prefijo PLACE/. Un salto significa "
                  "que la llave place_id dejó de resolver.", 3)
        else:
            R.add(BIEN, "Coherencia",
                  "Cruce con el catálogo: %d sin equivalencia de %d (%.2f%%)"
                  % (len(sin), len(U), pct))


# ─────────────────────────────────────────────────────────────────────
#  FUNCIONAL — abrir el sitio y comprobar que los números cuadran
#
#  Esto es lo que faltaba. Los bloques anteriores verifican que los
#  parches existan y que los archivos compilen; ninguno comprobaba que el
#  producto FUNCIONE ni que lo que muestra en pantalla coincida con lo que
#  dicen los CSV. Un tablero puede pasar todos los centinelas y mostrar
#  una cifra equivocada, que es exactamente el daño que importa: el
#  cliente puede descargar el mismo padrón y comprobarlo.
#
#  Cada cifra se recalcula aquí en Python, por separado, y se compara con
#  la que el navegador pintó. Si no coinciden, es CRÍTICO.
#
#  Necesita node, playwright y Chromium. Donde no estén —el runner de
#  GitHub Actions, por ejemplo— el bloque se declara omitido en vez de
#  fingir que pasó.
# ─────────────────────────────────────────────────────────────────────
SONDA_JS = r"""
import { chromium } from 'playwright';
const PUERTO = process.argv[2];
const out = { errores: [], faltantes: [], csp: [], datos: {} };
const b = await chromium.launch({ executablePath: process.env.CHROMIUM_BIN });
const p = await b.newPage({ viewport: { width: 1440, height: 1200 } });
p.on('pageerror', e => out.errores.push(String(e.message).slice(0, 200)));
p.on('response', r => {
  if (r.status() === 404) {
    const u = new URL(r.url()).pathname;
    if (!/tile|openstreetmap/.test(u)) out.faltantes.push(u);
  }
});
p.on('console', m => {
  const t = m.text();
  if (/Content Security Policy|Refused to/i.test(t)) out.csp.push(t.slice(0, 160));
});
const T = async s => { try { return (await p.innerText(s)).replace(/\s+/g, ' ').trim(); }
                       catch (e) { return null; } };
try {
  await p.goto('http://127.0.0.1:' + PUERTO + '/index.html',
               { waitUntil: 'networkidle', timeout: 120000 });
  await p.waitForTimeout(9000);
  await p.click('#consentOk').catch(() => {});

  // Un corte concreto: el más reciente del selector
  const periodos = await p.$$eval('#periodSelect option', o => o.map(x => x.value));
  const corte = periodos.filter(v => v)[0] || '';
  if (corte) { await p.selectOption('#periodSelect', corte); await p.waitForTimeout(3500); }
  out.datos.corte = corte;
  out.datos.tabla_corte = await T('#tableCount');
  out.datos.tope_corte  = await T('#topeNote');
  out.datos.tope_tarjetas = await p.$$eval('#topeCards .tope__card',
      e => e.map(x => x.innerText.replace(/\s+/g, ' ').trim())).catch(() => []);
  out.datos.operador = await T('#compNote');

  // El radio, que es donde vivió el fallo
  await p.evaluate(() => document.querySelectorAll('details').forEach(d => { d.open = true; }));
  await p.waitForTimeout(500);
  await p.fill('#vecSearch', 'Guadalajara');
  await p.waitForTimeout(2200);
  const ops = await p.$$eval('#vecStation option', o => o.slice(0, 2).map(x => x.value));
  if (ops.length) {
    out.datos.vec_permiso = ops[0];
    await p.selectOption('#vecStation', ops[0]);
    await p.waitForTimeout(2200);
    out.datos.vec_corte = await p.$$eval('#vecResumen .vec__dato',
        e => e.map(x => x.innerText.replace(/\s+/g, ' ').trim()));
  }

  // Todos los periodos: el radio DEBE dar lo mismo
  await p.selectOption('#periodSelect', '');
  await p.waitForTimeout(4000);
  out.datos.tabla_todos = await T('#tableCount');
  if (ops.length) {
    await p.fill('#vecSearch', 'Guadalajara');
    await p.waitForTimeout(2000);
    await p.selectOption('#vecStation', ops[0]).catch(() => {});
    await p.waitForTimeout(2200);
    out.datos.vec_todos = await p.$$eval('#vecResumen .vec__dato',
        e => e.map(x => x.innerText.replace(/\s+/g, ' ').trim()));
  }

  // La dinámica SÍ debe seguir viendo los varios cortes
  await p.click('[data-prof="dinamica"]').catch(() => {});
  await p.waitForTimeout(3000);
  out.datos.dinamica = await T('#dinCortes');

  // Paneles que no pueden quedar vacíos
  for (const [k, sel] of [['kpis', '#dinKpis'], ['conducta', '#condCards'],
                          ['tope', '#topeCards'], ['competencia', '#compCards']]) {
    const t = await T(sel);
    out.datos['vacio_' + k] = !t || t.length < 3;
  }

  // Tema claro/oscuro: el error 5 dejó las gráficas ilegibles
  const antes = out.errores.length;
  await p.click('#btnTema').catch(async () => { await p.click('[data-tema]').catch(() => {}); });
  await p.waitForTimeout(2500);
  out.datos.tema_rompe = out.errores.length > antes;

  // Privacidad y consentimiento
  await p.click('#btnPrivacidad').catch(() => {});
  await p.waitForTimeout(800);
  out.datos.aviso_abre = await p.isVisible('#avisoModal').catch(() => false);
} catch (e) {
  out.errores.push('SONDA: ' + String(e.message).slice(0, 200));
}
await b.close();
console.log('###JSON###' + JSON.stringify(out));
"""


def _num(txt):
    """Primer entero con separadores de miles que aparezca en el texto."""
    if not txt:
        return None
    m = re.search(r"(\d[\d,]*)", txt.replace(" ", " "))
    return int(m.group(1).replace(",", "")) if m else None


def bloque_funcional(raiz, R):
    import shutil
    import socket
    import tempfile
    import threading

    chromium = os.environ.get("CHROMIUM_BIN") or "/opt/pw-browsers/chromium"
    if not _hay("node") or not os.path.exists(chromium):
        R.add(AVISO, "Funcional", "Bloque omitido: falta node o Chromium",
              "Se verificó el código y los datos, NO que el sitio funcione. "
              "En la sesión del lunes sí corre.")
        return
    pw = None
    for cand in ("/home/claude/merge/node_modules", "/home/claude/patches/node_modules",
                 os.path.join(raiz, "node_modules")):
        if os.path.isdir(os.path.join(cand, "playwright")):
            pw = cand
            break
    if not pw:
        R.add(AVISO, "Funcional", "Bloque omitido: falta playwright",
              "Instálalo con `npm i playwright` para que la auditoría abra el sitio.")
        return

    # Servidor local sobre una copia del repo
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(puerto)],
                           cwd=raiz, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    tmp = tempfile.mkdtemp(prefix="aud-func-")
    try:
        import time
        time.sleep(2)
        js = os.path.join(tmp, "sonda.mjs")
        with io.open(js, "w", encoding="utf-8") as h:
            h.write(SONDA_JS)
        env = dict(os.environ)
        env["NODE_PATH"] = pw
        env["CHROMIUM_BIN"] = chromium
        # node resuelve los imports desde el directorio del script
        os.symlink(pw, os.path.join(tmp, "node_modules"))
        r = subprocess.run(["node", js, str(puerto)], capture_output=True,
                           env=env, timeout=300, cwd=tmp)
        salida = r.stdout.decode("utf-8", "replace")
        if "###JSON###" not in salida:
            R.add(ALERTA, "Funcional", "La sonda del navegador no devolvió resultado",
                  (r.stderr.decode("utf-8", "replace")[-240:] or salida[-240:]))
            return
        d = json.loads(salida.split("###JSON###", 1)[1].strip())
    except Exception as e:
        R.add(ALERTA, "Funcional", "No se pudo abrir el sitio",
              "%s: %s" % (type(e).__name__, str(e)[:180]))
        return
    finally:
        srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- errores del navegador ----
    if d["errores"]:
        R.add(CRITICO, "Funcional", "%d error(es) de JavaScript en el sitio"
              % len(d["errores"]), " | ".join(d["errores"][:3]))
    else:
        R.add(BIEN, "Funcional", "El sitio carga sin un solo error de JavaScript")
    if d["faltantes"]:
        R.add(ALERTA, "Funcional", "Archivos que el navegador pidió y no existen",
              ", ".join(sorted(set(d["faltantes"]))[:6]), 11)
    otras = [c for c in d["csp"] if "frame-ancestors" not in c]
    if otras:
        R.add(ALERTA, "Funcional", "La política de seguridad bloqueó algo",
              " | ".join(otras[:2]))

    dat = d["datos"]
    vacios = [k[6:] for k in dat if k.startswith("vacio_") and dat[k]]
    if vacios:
        R.add(CRITICO, "Funcional", "Paneles vacíos en pantalla: %s" % ", ".join(vacios),
              "Renderizaron sin contenido. Un panel en blanco es peor que ausente.")
    if dat.get("tema_rompe"):
        R.add(CRITICO, "Funcional", "Cambiar de tema produce errores de JavaScript",
              "Es el error 5: hay que destruir las instancias de Chart.js.", 5)
    elif "tema_rompe" in dat:
        R.add(BIEN, "Funcional", "El cambio de tema no rompe las gráficas")
    if dat.get("aviso_abre"):
        R.add(BIEN, "Funcional", "El aviso de privacidad abre desde el pie")
    else:
        R.add(ALERTA, "Funcional", "No se pudo abrir el aviso de privacidad",
              "Es obligatorio por LFPDPPP y es lo que un cliente corporativo audita.")

    # ---- LA PRUEBA QUE IMPORTA: la pantalla contra los CSV ----
    fb = filas(os.path.join(raiz, "fallback.csv"))
    if not fb:
        return
    corte = dat.get("corte") or max(r["Fecha"] for r in fb)
    U = [r for r in fb if r["Fecha"] == corte]
    est_real = len({(r.get("Permiso CRE") or "").strip() for r in U})
    est_pantalla = _num(dat.get("tabla_corte"))
    if est_pantalla is None:
        R.add(ALERTA, "Funcional", "No se pudo leer el conteo de la tabla")
    elif est_pantalla != est_real:
        R.add(CRITICO, "Funcional",
              "La tabla miente: muestra %s estaciones y el padrón tiene %s"
              % ("{:,}".format(est_pantalla), "{:,}".format(est_real)),
              "Corte %s. Recalculado en Python contra fallback.csv. Es la clase "
              "de fallo de los errores 6, 15 y 18." % corte, 18)
    else:
        R.add(BIEN, "Funcional",
              "La tabla coincide con el padrón: %s estaciones en el corte %s"
              % ("{:,}".format(est_real), corte))

    # Cumplimiento del tope, recalculado aparte
    prod, tope = "Regular", 24.00
    vals = [round(float(r[prod]) * 100) for r in U if (r.get(prod) or "").strip()]
    if vals and dat.get("tope_tarjetas"):
        tc = round(tope * 100)
        n = len(vals)
        fuera = sum(1 for x in vals if x > tc)
        justo = sum(1 for x in vals if x == tc)
        esperado = {
            "cumple": round((n - fuera - justo) / float(n) * 1000) / 10.0,
            "justo": round(justo / float(n) * 1000) / 10.0,
            "fuera": round(fuera / float(n) * 1000) / 10.0,
        }
        vistos = []
        for t in dat["tope_tarjetas"]:
            m = re.search(r"(\d+\.\d)%", t)
            if m:
                vistos.append(float(m.group(1)))
        if len(vistos) == 3:
            esp = [esperado["cumple"], esperado["justo"], esperado["fuera"]]
            if any(abs(a - b) > 0.15 for a, b in zip(vistos, esp)):
                R.add(CRITICO, "Funcional",
                      "El panel del tope no cuadra con el padrón",
                      "Pantalla %s · recalculado %s (cumple/justo/fuera, %s)"
                      % (vistos, esp, prod), 18)
            else:
                R.add(BIEN, "Funcional",
                      "El panel del tope cuadra: %s%% cumple, %s%% justo, %s%% fuera"
                      % tuple(esp))

    # Paridad del radio entre un corte y todos los periodos
    a = dat.get("vec_corte") or []
    b = dat.get("vec_todos") or []
    if a and b:
        na = _num(" ".join(x for x in a if "COMPETIDORES" in x.upper()))
        nb = _num(" ".join(x for x in b if "COMPETIDORES" in x.upper()))
        if na is not None and nb is not None:
            if na != nb:
                R.add(CRITICO, "Funcional",
                      "El radio cambia con el selector de periodo: %d contra %d"
                      % (na, nb),
                      "Con un corte da %d competidores y con «Todos los periodos» %d. "
                      "Es el error 18: se están contando registros, no estaciones."
                      % (na, nb), 18)
            else:
                R.add(BIEN, "Funcional",
                      "El radio da %d competidores con un corte y con todos los "
                      "periodos" % na)

    # La dinámica, en cambio, SÍ debe ver varios cortes
    din = dat.get("dinamica") or ""
    nd = _num(din)
    if nd is not None and nd < 2:
        R.add(CRITICO, "Funcional",
              "La dinámica dejó de ver varios cortes",
              "Dice «%s». Mide el movimiento ENTRE cortes: con uno solo no mide "
              "nada. Alguien le pasó el conjunto colapsado." % din, 15)
    elif nd is not None:
        R.add(BIEN, "Funcional", "La dinámica sigue viendo varios cortes", din)


def imprimir(R, markdown=False):
    orden = [CRITICO, ALERTA, AVISO, BIEN]
    etiqueta = {CRITICO: "CRÍTICO", ALERTA: "ALERTA", AVISO: "AVISO", BIEN: "OK"}
    sal = []
    nc, na = len(R.por_sev(CRITICO)), len(R.por_sev(ALERTA))
    if markdown:
        sal.append("# Auditoría del tablero · %s" % HOY.isoformat())
        sal.append("")
        if nc:
            sal.append("## %d hallazgo(s) CRÍTICO(s) — no publiques publicidad hasta resolverlos" % nc)
        elif na:
            sal.append("## Sin críticos · %d alerta(s) para esta semana" % na)
        else:
            sal.append("## Todo en orden")
        sal.append("")
    else:
        sal.append("=" * 72)
        sal.append("AUDITORÍA LB GAS 23 · %s" % HOY.isoformat())
        sal.append("=" * 72)
    for sev in orden:
        items = R.por_sev(sev)
        if not items:
            continue
        if markdown:
            sal.append("### %s (%d)" % (etiqueta[sev], len(items)))
            for i in items:
                ref = " · error %d" % i["err"] if i["err"] else ""
                sal.append("- **%s** — %s%s" % (i["bloque"], i["titulo"], ref))
                if i["detalle"]:
                    sal.append("  %s" % i["detalle"])
            sal.append("")
        else:
            for i in items:
                ref = " [error %d]" % i["err"] if i["err"] else ""
                sal.append("%-8s %-13s %s%s" % (etiqueta[sev], i["bloque"], i["titulo"], ref))
                if i["detalle"] and sev in (CRITICO, ALERTA):
                    for ln in re.findall(r".{1,66}(?:\s|$)", i["detalle"]):
                        if ln.strip():
                            sal.append("                       %s" % ln.strip())
    if not markdown:
        sal.append("-" * 72)
        sal.append("%d crítico(s) · %d alerta(s) · %d aviso(s) · %d verificación(es) en orden"
                   % (nc, na, len(R.por_sev(AVISO)), len(R.por_sev(BIEN))))
    return "\n".join(sal)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    markdown = "--markdown" in sys.argv
    raiz = args[0] if args else "."
    if not os.path.isdir(raiz):
        sys.exit("No existe el directorio: %s" % raiz)

    R = Reporte()
    bloques = [bloque_estructura, bloque_centinela, bloque_sintaxis,
               bloque_referencias, bloque_series, bloque_padron, bloque_coherencia,
               bloque_codigo, bloque_clientes, bloque_flujo, bloque_git]
    if "--sin-navegador" not in sys.argv:
        bloques.insert(2, bloque_funcional)
    for fn in bloques:
        try:
            fn(raiz, R)
        except Exception as e:
            R.add(ALERTA, "Auditoría", "El bloque %s falló" % fn.__name__,
                  "%s: %s" % (type(e).__name__, str(e)[:200]))
    print(imprimir(R, markdown))
    return 1 if R.falla() else 0


if __name__ == "__main__":
    sys.exit(main())
