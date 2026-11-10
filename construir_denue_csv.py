#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera denue.csv: enriquecimiento por permiso para el tablero.

Cruza el catálogo de estaciones de la CNE contra el DENUE del INEGI
(clase SCIAN 468411, "Comercio al por menor de gasolina y diesel") y escribe
una fila por permiso con el nombre comercial, el domicilio, el código postal
y el estrato de personal ocupado.

ASIGNACIÓN ÚNICA — por qué este script se reescribió
----------------------------------------------------
La versión anterior asignaba a cada permiso **todo** establecimiento que
cayera dentro de 150 m. En una avenida con dos gasolineras cercanas eso le
colgaba el mismo establecimiento a los dos permisos: 303 establecimientos
repartidos entre 611 permisos, el 5.7%. En el tablero se veía como dos
estaciones distintas con el mismo rótulo —COMBUSTIBLES PALMA REAL aparecía
sobre ECOESTACION DE COMBUSTIBLES, a 145 m— y es el error 22.

Aquí el emparejamiento es **uno a uno**: se generan todos los pares
(permiso, establecimiento) dentro de la tolerancia, se ordenan por distancia
y se asignan de forma glotona, saltando cualquier par cuyo permiso o
establecimiento ya esté tomado. Así gana el par mutuamente más cercano y
ningún establecimiento queda colgado de dos permisos. Lo que no alcanza
pareja se queda SIN nombre comercial, que es la respuesta honesta: el tablero
cae a la razón social de la CNE (regla 1.1).

La columna `Metros` deja a la vista la distancia del cruce, para que la
calidad del emparejamiento sea auditable y no haya que creerle al script.

Uso
---
    python3 construir_denue_csv.py \\
        --denue INEGI_DENUE_09112026.csv \\
        --catalogo catalogo_estaciones.csv \\
        --salida denue.csv \\
        [--tolerancia 150]

El CSV del INEGI viene en latin-1. El de salida va en UTF-8, como el resto
del repositorio.
"""
import argparse
import csv
import io
import math
import re
import sys
import unicodedata
from collections import defaultdict

SCIAN_ESTACION = "468411"


def clave_permiso(p):
    k = re.sub(r"\s+", "", str(p or "")).upper()
    return k[4:] if k.startswith("CNE/") else k


def limpia(s):
    """Colapsa espacios y nada más: los acentos se conservan.

    Una versión anterior de este script normalizaba a ASCII y escribía
    «ESPANA CORPORATIVO» y «ESTACION DE SERVICIO». El nombre va a pantalla:
    se guarda como lo publica el INEGI.
    """
    return re.sub(r"\s+", " ", str(s or "")).strip()


def sin_acentos(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


#  Algunos registros del DENUE traen como "nombre" la descripción de la clase
#  SCIAN en vez del nombre del negocio. Eso no identifica nada en la calle, así
#  que la fila se conserva —el domicilio y el personal sí sirven— pero el
#  nombre se deja vacío y el tablero cae a la razón social.
GENERICO = re.compile(r"^COMERCIO AL POR MENOR DE GASOLINA", re.I)


def comercial(s):
    t = limpia(s)
    return "" if GENERICO.match(sin_acentos(t)) else t


def haversine(la1, lo1, la2, lo2):
    r = 6371000.0
    p = math.radians
    x = (math.sin(p(la2 - la1) / 2) ** 2 +
         math.cos(p(la1)) * math.cos(p(la2)) * math.sin(p(lo2 - lo1) / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(x))


def columna(campos, *fragmentos):
    """El INEGI cambia la redacción de los encabezados entre publicaciones."""
    for frag in fragmentos:
        for c in campos:
            if frag.lower() in c.lower():
                return c
    return None


def domicilio(r, c):
    """Mismo formato que la versión anterior, para no romper lo que ya se lee."""
    via = " ".join(x for x in (r.get(c["tipo_via"], ""), r.get(c["via"], ""),
                               r.get(c["num"], "")) if x and x.strip()).strip()
    asen = " ".join(x for x in (r.get(c["tipo_asen"], ""), r.get(c["asen"], ""))
                    if x and x.strip()).strip()
    partes = [p for p in (via, asen, (r.get(c["mun"], "") or "").strip()) if p]
    return ", ".join(partes)


def main():
    ap = argparse.ArgumentParser(description="Genera denue.csv con asignación única.")
    ap.add_argument("--denue", required=True, help="CSV del DENUE (INEGI, latin-1)")
    ap.add_argument("--catalogo", required=True, help="catalogo_estaciones.csv")
    ap.add_argument("--salida", default="denue.csv")
    ap.add_argument("--tolerancia", type=float, default=150.0,
                    help="Distancia máxima del cruce, en metros (por omisión 150)")
    args = ap.parse_args()

    # ---- catálogo de la CNE ----
    with io.open(args.catalogo, encoding="utf-8-sig", newline="") as fh:
        cat = list(csv.DictReader(fh))
    estaciones = []
    for r in cat:
        try:
            la, lo = float(r["Lat"]), float(r["Lon"])
        except (TypeError, ValueError, KeyError):
            continue
        if not (14.0 <= la <= 33.0 and -118.5 <= lo <= -86.0):
            continue
        k = clave_permiso(r.get("Permiso CRE"))
        if k:
            estaciones.append((k, la, lo))
    if not estaciones:
        sys.exit("El catálogo no trajo ninguna estación con coordenada válida.")

    # ---- DENUE ----
    with io.open(args.denue, encoding="latin-1", newline="") as fh:
        den = list(csv.DictReader(fh))
    if not den:
        sys.exit("El CSV del DENUE vino vacío.")
    campos = list(den[0].keys())
    c = {
        "nombre":    columna(campos, "Nombre de la Unidad"),
        "scian":     columna(campos, "clase de actividad SCIAN", "SCIAN"),
        "personal":  columna(campos, "estrato personal"),
        "tipo_via":  columna(campos, "Tipo de vialidad"),
        "via":       columna(campos, "Nombre de la vialidad"),
        "num":       columna(campos, "exterior o kil"),
        "tipo_asen": columna(campos, "Tipo de asentamiento"),
        "asen":      columna(campos, "Nombre de asentamiento"),
        "cp":        columna(campos, "Postal"),
        "mun":       columna(campos, "Municipio"),
        "lat":       columna(campos, "Latitud"),
        "lon":       columna(campos, "Longitud"),
    }
    faltan = [k for k, v in c.items() if not v]
    if faltan:
        sys.exit("El CSV del DENUE no trae estas columnas: %s" % ", ".join(faltan))

    # Regla 1.5: valida contenido, no el nombre del archivo. Si la descarga no
    # es de la clase 468411 el cruce entero saldría mal, en silencio.
    clases = {(r.get(c["scian"]) or "").strip() for r in den}
    otras = clases - {SCIAN_ESTACION, ""}
    if otras:
        sys.exit("El DENUE trae clases SCIAN ajenas a %s: %s. Descarga el padrón "
                 "de la clase 468411." % (SCIAN_ESTACION, ", ".join(sorted(otras)[:5])))

    sitios = []
    for r in den:
        try:
            la, lo = float(r[c["lat"]]), float(r[c["lon"]])
        except (TypeError, ValueError):
            continue
        if not (14.0 <= la <= 33.0 and -118.5 <= lo <= -86.0):
            continue
        sitios.append((la, lo, r))

    # ---- rejilla espacial: comparar todo contra todo son 200 millones de pares ----
    tol = args.tolerancia
    paso = 0.02                      # ~2.2 km de lado, holgado para 150 m
    malla = defaultdict(list)
    for i, (la, lo, _r) in enumerate(sitios):
        malla[(int(la / paso), int(lo / paso))].append(i)

    pares = []
    for k, la, lo in estaciones:
        gi, gj = int(la / paso), int(lo / paso)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for i in malla.get((gi + di, gj + dj), ()):
                    d = haversine(la, lo, sitios[i][0], sitios[i][1])
                    if d <= tol:
                        pares.append((d, k, i))

    # ---- asignación glotona por distancia: uno a uno ----
    pares.sort()
    tomado_permiso, tomado_sitio, asignado = set(), set(), {}
    for d, k, i in pares:
        if k in tomado_permiso or i in tomado_sitio:
            continue
        tomado_permiso.add(k)
        tomado_sitio.add(i)
        asignado[k] = (i, d)

    # ---- salida ----
    with io.open(args.salida, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["Permiso CRE", "Nombre comercial", "Direccion", "CP",
                    "Personal", "Metros"])
        for k in sorted(asignado):
            i, d = asignado[k]
            r = sitios[i][2]
            w.writerow([k,
                        comercial(r.get(c["nombre"])),
                        domicilio(r, c),
                        (r.get(c["cp"]) or "").strip(),
                        (r.get(c["personal"]) or "").strip(),
                        int(round(d))])

    disputados = len(pares) - len(asignado)
    print("Estaciones del catálogo con coordenada : %d" % len(estaciones))
    print("Establecimientos del DENUE             : %d" % len(sitios))
    print("Pares dentro de %-4.0f m                 : %d" % (tol, len(pares)))
    print("Emparejados uno a uno                  : %d (%.1f%% del catálogo)"
          % (len(asignado), 100.0 * len(asignado) / len(estaciones)))
    print("Pares descartados por doble reclamo    : %d" % disputados)
    print("Escrito: %s" % args.salida)


if __name__ == "__main__":
    main()
