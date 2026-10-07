#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de instancias por cliente — Monitor de Precios
========================================================

Arma la carpeta lista para publicar de un cliente concreto: su marca, sus
estaciones, su radio de competencia y —si se indica— solo los datos de su
estado, de modo que una copia filtrada valga poco fuera de su plaza.

Uso
---
    python3 preparar_cliente.py \
        --origen . \
        --slug lbgas23 \
        --nombre "LB GAS 23" \
        --subtitulo "Servicio Bautista · Precios al Público (SENER / CNE / SAT)" \
        --permisos "PL/7773/EXP/ES/2015,PL/12668/EXP/ES/2015" \
        --estado Jalisco \
        --radio 5 \
        --logo logo_lbgas23.png \
        --salida clientes/lbgas23

El resultado es una carpeta autónoma que se sube a su propio hosting (o a una
subcarpeta del repositorio). Los datos nacionales se regeneran una vez al día;
este script solo recorta y reetiqueta, así que correrlo cuesta segundos.
"""

import argparse
import csv
import datetime
import io
import os
import re
import shutil
import sys

# Archivos que toda instancia necesita. config.js NO va aquí: se escribe aparte.
# Cascarón compacto: index.html lleva CSS, librerías, logotipo y aplicación
# embebidos. manifest.json, sw.js y los iconos van aparte porque el navegador
# los exige como archivos independientes para la instalación y el modo offline.
ARCHIVOS_APP = [
    "index.html", "sw.js", "manifest.json",
    "favicon.png", "apple-touch-icon.png",
    "icono-192.png", "icono-512.png", "icono-512-maskable.png",
    ".nojekyll",
]

DATOS = ["fallback.csv", "historico.csv", "catalogo_estaciones.csv", "reporte_mercado.csv"]


def normaliza_permiso(p):
    k = "".join(str(p or "").split()).upper()
    return k[4:] if k.startswith("CNE/") else k


def filtrar_csv(origen, destino, columna, valor):
    """Copia un CSV conservando solo las filas de un estado. Devuelve (leídas, escritas)."""
    with io.open(origen, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    if not filas or columna not in filas[0]:
        shutil.copy(origen, destino)
        return len(filas), len(filas)
    quiere = set(v.strip().lower() for v in (valor if isinstance(valor, (list, tuple)) else [valor]) if v.strip())
    conservadas = [f for f in filas if (f.get(columna) or "").strip().lower() in quiere]
    with io.open(destino, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(conservadas)
    return len(filas), len(conservadas)


def filtrar_historico(origen, destino, estados):
    """El histórico guarda ámbitos: se conservan el nacional y el de cada estado."""
    with io.open(origen, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    if not filas:
        shutil.copy(origen, destino)
        return 0, 0
    quiere = set(v.strip().lower() for v in (estados if isinstance(estados, (list, tuple)) else [estados]) if v.strip())
    conservadas = [f for f in filas
                   if (f.get("Ambito") == "nacional")
                   or ((f.get("Ambito") == "estado") and (f.get("Clave", "").lower() in quiere))]
    with io.open(destino, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(conservadas)
    return len(filas), len(conservadas)


def construir_config(args, permisos, logo):
    js = '''window.APP_CONFIG = {

  /* ---------- Fuentes de datos ---------- */
  SHEET_CSV_URL: "",
  CSV_URL: "",
  XML_URL: "",
  FALLBACK_CSV: "fallback.csv",
  CATALOG_CSV: "catalogo_estaciones.csv",
  HISTORY_CSV: "historico.csv",
  REPORT_CSV: "reporte_mercado.csv",

  /* ---------- Plan contratado ---------- */
  MIS_MAX: %(max_estaciones)d,

  /* ---------- Comportamiento ---------- */
  REFRESH_MINUTES: %(refresco)d,
  SEARCH_DEBOUNCE_MS: 180,
  PAGE_SIZE: 25,
  PRICE_MIN: 15,
  PRICE_MAX: 45,
  RADIO_KM: %(radio)s,
  MAPA_MAX_PUNTOS: 2500,
  ELASTICIDAD_PCT_POR_10_CENTAVOS: 2,
  ESTADO_POR_DEFECTO: "",
  MAPA_CENTRO: [%(centro)s],
  MAPA_ZOOM: %(zoom)d,
  HISTORY_XLSX: "%(xlsx)s",

  /* ---------- Identidad ---------- */
  TITLE: "%(nombre)s · Monitor de Precios",
  SUBTITLE: "%(subtitulo)s",
  LOGO_URL: "%(logo)s",
  REPO_URL: "",

  /* ---------- Estaciones del cliente ---------- */
  MIS_ESTACIONES: {
    permisos: [%(permisos)s],
    patrones: []
  },

  MARCAS_COMPETENCIA: ["BP", "TOTALENERGIES", "REPSOL", "SHELL", "CHEVRON",
                       "EXXONMOBIL", "GULF", "G500", "OXXO GAS", "ARCO NORTE"],

  /* Topes de la Estrategia Nacional (SENER y Presidencia, ago 2026 - feb 2027).
     Premium no está en el pacto. */
  TOPE_ESTRATEGIA: {
    label: "Estrategia Nacional SENER",
    vigencia: "20 ago 2026 – feb 2027",
    regular: %(tope_r)s,
    diesel: %(tope_d)s,
    premium: null
  },

  BENCHMARK: {
    label: "Promedio nacional",
    regular: %(bench_r)s,
    premium: %(bench_p)s,
    diesel: %(bench_d)s
  },

  METODOLOGIA: "Fuente: Valores estimados por la SENER con información de la CNE y el SAT. " +
               "El precio al público es un promedio de los precios registrados durante el periodo de referencia."
};
''' % {
        "nombre": args.nombre,
        "subtitulo": args.subtitulo,
        "logo": logo,
        "radio": args.radio,
        "max_estaciones": args.max_estaciones,
        "centro": args.centro,
        "zoom": args.zoom,
        "xlsx": args.xlsx,
        "refresco": args.refresco,
        "permisos": ", ".join('"%s"' % p for p in permisos),
        "bench_r": args.benchmark_regular,
        "bench_p": args.benchmark_premium,
        "bench_d": args.benchmark_diesel,
        "tope_r": args.tope_regular,
        "tope_d": args.tope_diesel,
    }
    return js.rstrip().rstrip(";")


def main():
    ap = argparse.ArgumentParser(description="Genera la instancia de un cliente.")
    ap.add_argument("--origen", default=".", help="Carpeta con la aplicación y los datos nacionales")
    ap.add_argument("--salida", required=True, help="Carpeta destino de la instancia")
    ap.add_argument("--slug", required=True, help="Identificador corto del cliente (sin espacios)")
    ap.add_argument("--nombre", required=True, help="Nombre comercial del cliente")
    ap.add_argument("--subtitulo", default="Monitor de precios de combustibles")
    ap.add_argument("--permisos", default="", help="Permisos CRE del cliente, separados por coma")
    ap.add_argument("--estado", default="", help="Recorta los datos a este estado (recomendado)")
    ap.add_argument("--estados", default="",
                    help="Varios estados separados por coma, p. ej. "
                         "\"Jalisco,Guanajuato,Michoacan\". Tiene prioridad sobre --estado.")
    ap.add_argument("--radio", default="5", help="Radio del mercado local en kilómetros")
    ap.add_argument("--max-estaciones", type=int, default=5, dest="max_estaciones",
                    help="Tope de estaciones propias: 1 Plan Estación, 5 Plan Red, 15 Plan Grupo")
    ap.add_argument("--centro", default="",
                    help="Encuadre inicial del mapa como 'lat,lon' (ej. 20.6736,-103.3440)")
    ap.add_argument("--zoom", type=int, default=12, help="Zoom inicial cuando se indica --centro")
    ap.add_argument("--xlsx", default="",
                    help="Archivo que descarga el botón Histórico (vacío: usa el CSV)")
    ap.add_argument("--logo", default="", help="Archivo de logotipo a copiar en la instancia")
    ap.add_argument("--refresco", type=int, default=10, help="Minutos entre actualizaciones automáticas")
    ap.add_argument("--tope-regular", default="24.00", dest="tope_regular",
                    help="Tope de la Estrategia Nacional para Regular")
    ap.add_argument("--tope-diesel", default="27.00", dest="tope_diesel",
                    help="Tope de la Estrategia Nacional para Diésel")
    ap.add_argument("--benchmark-regular", default="23.68")
    ap.add_argument("--benchmark-premium", default="28.50")
    ap.add_argument("--benchmark-diesel", default="27.00")
    args = ap.parse_args()

    if not re.match(r"^[a-z0-9][a-z0-9-]*$", args.slug):
        sys.exit("El slug debe ir en minúsculas, sin espacios ni acentos (ej. lbgas23).")

    if args.max_estaciones < 1:
        sys.exit("--max-estaciones debe ser 1 o más.")

    # El centro llega como "lat,lon" y se escribe como arreglo de JavaScript.
    if args.centro:
        partes = [p.strip() for p in args.centro.replace(";", ",").split(",") if p.strip()]
        if len(partes) != 2:
            sys.exit("--centro debe tener la forma 'lat,lon', por ejemplo 20.6736,-103.3440")
        try:
            args.centro = "%s, %s" % (float(partes[0]), float(partes[1]))
        except ValueError:
            sys.exit("--centro trae coordenadas que no son números.")

    os.makedirs(args.salida, exist_ok=True)

    # 1. Aplicación
    faltantes = []
    for archivo in ARCHIVOS_APP:
        origen = os.path.join(args.origen, archivo)
        if not os.path.exists(origen):
            faltantes.append(archivo)
            continue
        shutil.copy(origen, os.path.join(args.salida, archivo))
    if faltantes:
        sys.exit("Faltan archivos en --origen: %s" % ", ".join(faltantes))

    # 2. Logotipo (opcional: el index consolidado ya lo lleva embebido)
    logo = ""
    if args.logo:
        origen_logo = args.logo if os.path.exists(args.logo) else os.path.join(args.origen, args.logo)
        if not os.path.exists(origen_logo):
            sys.exit("No se encontró el logotipo: %s" % args.logo)
        logo = os.path.basename(origen_logo)
        shutil.copy(origen_logo, os.path.join(args.salida, logo))

    # 3. Datos, recortados a los estados indicados
    #    --estados (varios) tiene prioridad sobre --estado (uno).
    estados = [e.strip() for e in args.estados.split(",") if e.strip()] if args.estados \
        else ([args.estado] if args.estado else [])
    alcance = ", ".join(estados) if estados else "nacional"
    resumen = []
    for archivo in DATOS:
        origen = os.path.join(args.origen, archivo)
        destino = os.path.join(args.salida, archivo)
        if not os.path.exists(origen):
            resumen.append((archivo, 0, 0, "ausente"))
            continue
        if not estados:
            shutil.copy(origen, destino)
            resumen.append((archivo, 0, 0, "completo"))
            continue
        if archivo == "historico.csv":
            leidas, escritas = filtrar_historico(origen, destino, estados)
        elif archivo == "reporte_mercado.csv":
            shutil.copy(origen, destino)      # son agregados, no revelan estaciones
            leidas = escritas = 0
        else:
            leidas, escritas = filtrar_csv(origen, destino, "Estado", estados)
        resumen.append((archivo, leidas, escritas, "recortado"))

    # 4. Configuración: se reemplaza el bloque APP_CONFIG dentro del index.
    permisos = [normaliza_permiso(p) for p in args.permisos.split(",") if p.strip()]
    ruta_index = os.path.join(args.salida, "index.html")
    with io.open(ruta_index, encoding="utf-8") as fh:
        html = fh.read()
    bloque = construir_config(args, permisos, logo)
    ini = html.find("window.APP_CONFIG")
    if ini == -1:
        sys.exit("El index.html de origen no contiene el bloque window.APP_CONFIG.")
    fin = html.find("};", ini)
    if fin == -1:
        sys.exit("No se encontró el cierre del bloque window.APP_CONFIG.")
    html = html[:ini] + bloque + html[fin + 2:]
    with io.open(ruta_index, "w", encoding="utf-8") as fh:
        fh.write(html)

    # 5. Nota de entrega
    with io.open(os.path.join(args.salida, "INSTANCIA.md"), "w", encoding="utf-8") as fh:
        fh.write("# %s\n\n" % args.nombre)
        fh.write("Instancia generada con `preparar_cliente.py`.\n\n")
        fh.write("- Slug: `%s`\n" % args.slug)
        fh.write("- Estaciones declaradas: %s\n" % (", ".join(permisos) if permisos else "ninguna"))
        fh.write("- Radio de competencia: %s km\n" % args.radio)
        fh.write("- Tope de estaciones propias: %d\n" % args.max_estaciones)
        fh.write("- Alcance de datos: %s\n" % alcance)
        fh.write("- Generada: %s\n\n" % datetime.date.today().isoformat())
        fh.write("Para actualizar los datos, vuelve a correr el generador sobre la carpeta\n")
        fh.write("nacional ya actualizada. La configuracion se inyecta dentro de `index.html`\n")
        fh.write("(el bloque `window.APP_CONFIG`): no la edites a mano, se reescribe en cada\n")
        fh.write("corrida del generador.\n")

    print("Instancia creada en: %s" % args.salida)
    print("Cliente:            %s (%s)" % (args.nombre, args.slug))
    print("Estaciones:         %s" % (", ".join(permisos) if permisos else "ninguna declarada"))
    print("Alcance:            %s" % alcance)
    print("Tope de estaciones: %d (%s)" % (
        args.max_estaciones,
        "Plan Estación" if args.max_estaciones == 1 else
        "Plan Red" if args.max_estaciones <= 5 else
        "Plan Grupo" if args.max_estaciones <= 15 else "Plan Corporativo"))
    if args.centro:
        print("Encuadre inicial:   %s · zoom %d" % (args.centro, args.zoom))
    for archivo, leidas, escritas, modo in resumen:
        if modo == "recortado" and leidas:
            print("  %-24s %6d → %6d filas" % (archivo, leidas, escritas))
        else:
            print("  %-24s %s" % (archivo, modo))


if __name__ == "__main__":
    main()
