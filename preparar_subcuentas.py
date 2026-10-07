#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preparar_subcuentas.py — Subcuentas de clientes para una instancia comercializadora.

Genera una instancia por cada cliente de la comercializadora (estación de servicio
o flota compradora), ACOTADA AL RADIO DE COMPETENCIA DE SU PLAZA. Cada subcuenta
recibe únicamente las estaciones de su vecindario geográfico: no ve la región
completa, no ve la cartera de la comercializadora y no ve a los demás clientes.

El recorte es físico, no cosmético. Cada carpeta lleva su propio fallback.csv con
solo las filas de su radio; aunque alguien comparta la URL, lo que hay del otro
lado sigue siendo su propia plaza.

Uso:

    python3 preparar_subcuentas.py \\
        --origen . \\
        --padron clientes/enerso/subcuentas.csv \\
        --salida clientes/enerso/clientes

El padrón es un CSV con estas columnas (encabezado exacto):

    slug,nombre,permiso_cre,radio_km,radio_datos_km,zoom,activo

    slug             Identificador corto sin espacios (carpeta y URL).
    nombre           Nombre comercial del cliente, como lo verá en pantalla.
    permiso_cre      Permiso CRE de SU estación. Define el centro del recorte.
    radio_km         Radio de competencia que verá el tablero. Por omisión 5.
    radio_datos_km   Radio de los datos entregados. Por omisión radio_km * 3,
                     con un piso de 15 km, para que el municipio y la banda de
                     precios tengan masa estadística suficiente.
    zoom             Zoom inicial del mapa. Por omisión 13.
    activo           "si" / "no". Una subcuenta en "no" se omite y, si ya existía
                     la carpeta, se elimina: así se da de baja a un cliente que
                     dejó de comprarle a la comercializadora.

Salida: una carpeta por subcuenta activa, más un archivo ALTAS.md con el corte.
"""

import argparse
import csv
import datetime
import io
import math
import os
import shutil
import subprocess
import sys

DATOS_RECORTABLES = ("fallback.csv", "catalogo_estaciones.csv")
COLUMNAS = ("slug", "nombre", "permiso_cre", "radio_km", "radio_datos_km", "zoom", "activo")


def normaliza_permiso(p):
    k = "".join(str(p or "").split()).upper()
    return k[4:] if k.startswith("CNE/") else k


def distancia_km(lat1, lon1, lat2, lon2):
    """Haversine. La misma fórmula que usa el tablero, para que el recorte
    coincida exactamente con el radio que el cliente ve en pantalla."""
    r = 6371.0088
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def coordenadas_validas(lat, lon):
    """Caja envolvente de México. Una coordenada fuera de aquí no sirve como
    centro de un recorte: produciría una subcuenta vacía o absurda."""
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return 14.0 <= la <= 33.0 and -118.5 <= lo <= -86.0


def leer_catalogo(ruta):
    with io.open(ruta, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def ubicar(catalogo, permiso):
    """Devuelve (lat, lon, estado, municipio, estacion) de un permiso CRE."""
    objetivo = normaliza_permiso(permiso)
    for f in catalogo:
        if normaliza_permiso(f.get("Permiso CRE")) == objetivo:
            if not coordenadas_validas(f.get("Lat"), f.get("Lon")):
                return None
            return (float(f["Lat"]), float(f["Lon"]),
                    (f.get("Estado") or "").strip(),
                    (f.get("Municipio") or "").strip(),
                    (f.get("Estacion") or "").strip())
    return None


def permisos_en_radio(catalogo, lat, lon, radio):
    """Conjunto de permisos CRE dentro del radio. El catálogo es la única fuente
    de coordenadas: una estación sin coordenadas no puede entrar al recorte."""
    dentro = set()
    for f in catalogo:
        if not coordenadas_validas(f.get("Lat"), f.get("Lon")):
            continue
        if distancia_km(lat, lon, float(f["Lat"]), float(f["Lon"])) <= radio:
            dentro.add(normaliza_permiso(f.get("Permiso CRE")))
    return dentro


def recortar_por_permisos(ruta, permitidos):
    """Reescribe un CSV en su lugar conservando solo los permisos del conjunto."""
    with io.open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    if not filas or "Permiso CRE" not in filas[0]:
        return len(filas), len(filas)
    conservadas = [f for f in filas
                   if normaliza_permiso(f.get("Permiso CRE")) in permitidos]
    with io.open(ruta, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(conservadas)
    return len(filas), len(conservadas)


def estaciones_entregadas(ruta):
    """Estaciones únicas que de verdad quedaron en el recorte entregado."""
    if not os.path.exists(ruta):
        return 0
    with io.open(ruta, encoding="utf-8-sig", newline="") as fh:
        return len({normaliza_permiso(f.get("Permiso CRE")) for f in csv.DictReader(fh)})


def recortar_reporte(ruta):
    """El reporte comparativo trae bloques nacional, region y marca. Una subcuenta
    no debe llevarse el detalle regional: contradice la promesa de que solo ve su
    plaza. Se conserva unicamente el bloque nacional, que es la referencia publica
    que el tablero usa como benchmark, y se descartan los demas."""
    if not os.path.exists(ruta):
        return 0, 0
    with io.open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    if not filas or "Bloque" not in filas[0]:
        return len(filas), len(filas)
    conservadas = [f for f in filas if (f.get("Bloque") or "").strip().lower() == "nacional"]
    with io.open(ruta, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(conservadas)
    return len(filas), len(conservadas)


def leer_padron(ruta):
    with io.open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    if not filas:
        sys.exit("El padrón de subcuentas está vacío: %s" % ruta)
    faltan = [c for c in ("slug", "nombre", "permiso_cre") if c not in filas[0]]
    if faltan:
        sys.exit("Al padrón le faltan columnas obligatorias: %s" % ", ".join(faltan))
    return filas


def valor(fila, clave, omision):
    v = (fila.get(clave) or "").strip()
    return v if v else omision


def main():
    ap = argparse.ArgumentParser(description="Genera las subcuentas de clientes de una comercializadora.")
    ap.add_argument("--origen", default=".", help="Carpeta con la aplicación y los datos nacionales")
    ap.add_argument("--padron", required=True, help="CSV con el padrón de subcuentas")
    ap.add_argument("--salida", required=True, help="Carpeta donde se crean las subcuentas")
    ap.add_argument("--maximo", type=int, default=15,
                    help="Tope contratado de subcuentas activas (por omisión 15)")
    ap.add_argument("--logo", default="", help="Logotipo para todas las subcuentas")
    ap.add_argument("--tope-regular", default="24.00", dest="tope_regular")
    ap.add_argument("--tope-diesel", default="27.00", dest="tope_diesel")
    args = ap.parse_args()

    generador = os.path.join(args.origen, "preparar_cliente.py")
    if not os.path.exists(generador):
        sys.exit("No encuentro preparar_cliente.py en %s" % args.origen)

    ruta_catalogo = os.path.join(args.origen, "catalogo_estaciones.csv")
    if not os.path.exists(ruta_catalogo):
        sys.exit("No encuentro catalogo_estaciones.csv en %s" % args.origen)
    catalogo = leer_catalogo(ruta_catalogo)
    print("Catálogo nacional: %s estaciones" % format(len(catalogo), ","))

    filas = leer_padron(args.padron)
    activas = [f for f in filas if valor(f, "activo", "si").lower() in ("si", "sí", "s", "1", "true")]
    bajas = [f for f in filas if f not in activas]

    if len(activas) > args.maximo:
        sys.exit("El padrón trae %d subcuentas activas y el contrato permite %d. "
                 "Marca 'no' en la columna 'activo' a las que sobran antes de continuar."
                 % (len(activas), args.maximo))

    if not os.path.isdir(args.salida):
        os.makedirs(args.salida)

    # Baja: se elimina la carpeta para que el acceso deje de existir de verdad.
    for f in bajas:
        slug = valor(f, "slug", "")
        destino = os.path.join(args.salida, slug)
        if slug and os.path.isdir(destino):
            shutil.rmtree(destino)
            print("  BAJA  %-18s carpeta eliminada" % slug)

    bitacora = []
    for f in activas:
        slug = valor(f, "slug", "")
        nombre = valor(f, "nombre", slug)
        permiso = valor(f, "permiso_cre", "")
        if not slug or not permiso:
            print("  OMITE %-18s sin slug o sin permiso CRE" % (slug or "(sin slug)"))
            continue

        radio = float(valor(f, "radio_km", "5"))
        radio_datos = float(valor(f, "radio_datos_km", "0")) or max(15.0, radio * 3)
        zoom = int(valor(f, "zoom", "13"))

        sitio = ubicar(catalogo, permiso)
        if not sitio:
            print("  ERROR %-18s el permiso %s no está en el catálogo o no tiene "
                  "coordenadas válidas. No se genera." % (slug, permiso))
            continue
        lat, lon, estado, municipio, estacion = sitio

        destino = os.path.join(args.salida, slug)
        if os.path.isdir(destino):
            shutil.rmtree(destino)

        cmd = [sys.executable, generador,
               "--origen", args.origen,
               "--salida", destino,
               "--slug", slug,
               "--nombre", nombre,
               "--subtitulo", "Monitor de precios · %s" % (municipio or estado or "plaza local"),
               "--permisos", permiso,
               "--estado", estado,
               "--radio", str(radio),
               "--max-estaciones", "1",
               "--centro", "%.5f,%.5f" % (lat, lon),
               "--zoom", str(zoom),
               "--tope-regular", args.tope_regular,
               "--tope-diesel", args.tope_diesel]
        if args.logo:
            cmd += ["--logo", args.logo]

        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("  ERROR %-18s el generador falló:\n%s" % (slug, r.stderr.strip()[:400]))
            continue

        # Recorte geográfico: de la copia estatal nos quedamos solo con el radio.
        permitidos = permisos_en_radio(catalogo, lat, lon, radio_datos)
        permitidos.add(normaliza_permiso(permiso))
        antes = despues = 0
        for archivo in DATOS_RECORTABLES:
            ruta = os.path.join(destino, archivo)
            if os.path.exists(ruta):
                a, d = recortar_por_permisos(ruta, permitidos)
                if archivo == "fallback.csv":
                    antes, despues = a, d

        recortar_reporte(os.path.join(destino, "reporte_mercado.csv"))

        # El catálogo del radio y las estaciones que de verdad reportan precio no
        # son lo mismo: se informa lo entregado, no lo teóricamente cercano.
        entregadas = estaciones_entregadas(os.path.join(destino, "fallback.csv"))

        with io.open(os.path.join(destino, "SUBCUENTA.md"), "w", encoding="utf-8") as fh:
            fh.write("# %s\n\n" % nombre)
            fh.write("Subcuenta de cliente generada con `preparar_subcuentas.py`.\n\n")
            fh.write("- Slug: `%s`\n" % slug)
            fh.write("- Estación: %s\n" % (estacion or "—"))
            fh.write("- Permiso CRE: `%s`\n" % permiso)
            fh.write("- Plaza: %s\n" % ", ".join([x for x in (municipio, estado) if x]))
            fh.write("- Radio de competencia en pantalla: %s km\n" % radio)
            fh.write("- Radio de los datos entregados: %s km\n" % radio_datos)
            fh.write("- Estaciones que reportan precio en su recorte: %s\n" % format(entregadas, ","))
            fh.write("- Generada: %s\n\n" % datetime.date.today().isoformat())
            fh.write("Esta carpeta contiene únicamente las estaciones del radio anterior.\n")
            fh.write("No incluye la región completa ni la cartera de la comercializadora.\n")
            fh.write("Para dar de baja al cliente, marca `activo = no` en el padrón y vuelve\n")
            fh.write("a correr el generador: la carpeta se elimina.\n")

        bitacora.append((slug, nombre, estacion, municipio, estado, radio, radio_datos,
                         entregadas, antes, despues))
        print("  ALTA  %-18s %-28s %s · %s km · %s estaciones"
              % (slug, (estacion or nombre)[:28], municipio or estado, radio_datos,
                 format(entregadas, ",")))

    # Corte de altas, para que la comercializadora sepa qué entregó y a quién.
    with io.open(os.path.join(args.salida, "ALTAS.md"), "w", encoding="utf-8") as fh:
        fh.write("# Subcuentas activas\n\n")
        fh.write("Corte del %s · %d de %d subcuentas contratadas\n\n"
                 % (datetime.date.today().isoformat(), len(bitacora), args.maximo))
        fh.write("| Cliente | Estación | Plaza | Radio datos | Estaciones |\n")
        fh.write("|---|---|---|---|---|\n")
        for b in bitacora:
            fh.write("| %s | %s | %s | %s km | %s |\n"
                     % (b[1], b[2] or "—", ", ".join([x for x in (b[3], b[4]) if x]) or "—",
                        b[6], format(b[7], ",")))
        fh.write("\nCada subcuenta recibe solo las estaciones de su radio. ")
        fh.write("Dar de baja a un cliente es marcar `activo = no` en el padrón ")
        fh.write("y volver a correr el generador.\n")

    print("\n%d subcuenta(s) activa(s) de %d contratadas." % (len(bitacora), args.maximo))
    print("Corte de altas: %s" % os.path.join(args.salida, "ALTAS.md"))


if __name__ == "__main__":
    main()
