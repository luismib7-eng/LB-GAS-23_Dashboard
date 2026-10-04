#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de Precios de Combustibles — pipeline XML → CSV
=======================================================

Convierte el XML oficial de precios de la CNE al CSV que consume el tablero
(modalidad local / GitHub Actions de la arquitectura dual).

Uso
---
    # Genera fallback.csv, que es lo que config.js lee por omisión
    python3 xml_a_csv.py precios_2026-08-17.xml --catalogo catalogo_estaciones.csv

    # Acumula varios días en un histórico para activar la gráfica de tendencia
    python3 xml_a_csv.py precios_2026-08-18.xml --catalogo catalogo_estaciones.csv \
            --salida historico.csv --acumular

El XML solo trae permiso y precios; el catálogo aporta razón social, dirección,
municipio, estado y región. El cruce se hace por una clave canónica del permiso,
así que da igual si el catálogo trae espacios accidentales, minúsculas o el
prefijo "CNE/" que la Comisión adoptó en 2025 para los permisos nuevos.

Reglas de limpieza (idénticas a las de app.js, para que los números coincidan
sin importar la ruta de alimentación):
  · Precios fuera de --min/--max se descartan. El XML publica 0.01 o 1.00
    cuando la estación no reportó precio.
  · Permisos repetidos: se conserva el primer registro y solo se completan los
    productos que le falten.
  · Municipio, Estado y Región vacíos se escriben como "No especificado" para
    no dejar comas nulas consecutivas en el CSV.

Codificación: lectura y escritura en UTF-8 (se acepta BOM en el catálogo). Los
acentos de razones sociales y domicilios se conservan tal cual.
"""

import argparse
import csv
import datetime
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

COLUMNAS = ["Fecha", "Region", "Estado", "Municipio", "Marca", "Estacion",
            "Permiso CRE", "Direccion", "Regular", "Premium", "Diesel"]

COLUMNAS_HISTORICO = ["Fecha", "Ambito", "Clave", "Producto", "Promedio", "Estaciones"]

PRODUCTOS = {"regular": "Regular", "premium": "Premium", "diesel": "Diesel"}

SIN_DATO = "No especificado"

# Campos que reciben marcador cuando el catálogo no aporta el dato.
CON_MARCADOR = ("Region", "Estado", "Municipio")

# Encabezados aceptados en el catálogo, sin distinguir mayúsculas ni acentos.
ALIAS_CATALOGO = {
    "permiso": ["permiso cre", "permisocre", "numero", "num permiso", "permiso", "cre id", "cre_id"],
    "place_id": ["place id", "place_id", "placeid", "id"],
    "lat": ["lat", "latitud", "latitude", "y"],
    "lon": ["lon", "lng", "longitud", "longitude", "x"],
    "estacion": ["estacion", "razon social", "nombre"],
    "marca": ["marca", "bandera", "marca comercial"],
    "direccion": ["direccion", "domicilio"],
    "municipio": ["municipio", "ciudad", "localidad"],
    "estado": ["estado", "entidad", "entidad federativa"],
    "region": ["region", "zona"],
}


def norm_encabezado(h):
    """Minúsculas, sin acentos y sin espacios de sobra."""
    s = (h or "").strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u")):
        s = s.replace(a, b)
    return " ".join(s.split())


def clave_permiso(permiso):
    """
    Clave canónica para cruzar catálogos capturados con distintas convenciones:
    mayúsculas, sin espacios internos y sin el prefijo 'CNE/'.
        ' cne/pl/14/exp/es/2025 ' → 'PL/14/EXP/ES/2025'
        'PL/14/EXP/ES/2025'       → 'PL/14/EXP/ES/2025'
    """
    k = "".join(str(permiso or "").split()).upper()
    return k[4:] if k.startswith("CNE/") else k


# Formatos observados en las publicaciones de la CNE:
#   PL/658/EXP/ES/2015        estación de servicio
#   PL/11525/EXP/ESA/2015     estación de servicio para autoconsumo
#   PL/22553/EXP/ES/MM/2019   con segmento adicional
#   CNE/PL/138/EXP/ES/2025    permisos emitidos desde 2025
#   PL/1234/TRA/OM/2017       otras modalidades
PERMISO_RE = re.compile(r"(CNE/)?PL/\d+(?:/[A-Z.]{1,4})+/\d{4}", re.I)


def leer_catalogo_xml(ruta):
    """
    Catálogo desde el XML de estaciones que publica la CNE junto con los
    precios (endpoint .../publicaciones/places).

    El lector es deliberadamente tolerante: recorre cualquier elemento que
    contenga una cadena con forma de permiso —en un atributo o en un hijo— y
    toma el nombre y el domicilio de los hijos cuyo nombre de etiqueta lo
    sugiera. Así funciona aunque el esquema del endpoint cambie de nombres.
    """
    idx = {}
    raiz = leer_xml(ruta)

    def compacta(nombre):
        """Etiqueta comparable: sin espacio de nombres, sin acentos, sin
        separadores y en minúsculas. Así 'CreId', 'cre_id' y '{ns}CRE-ID'
        son la misma clave."""
        t = str(nombre or "").split("}")[-1].lower()
        for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
            t = t.replace(a, b)
        return re.sub(r"[^a-z0-9]", "", t)

    def texto_de(nodo, claves):
        objetivo = set(compacta(k) for k in claves)
        for hijo in nodo.iter():
            if hijo is nodo:
                continue
            if compacta(hijo.tag) in objetivo and (hijo.text or "").strip():
                return hijo.text.strip()
            for attr in hijo.attrib:                 # atributos de los hijos
                if compacta(attr) in objetivo and hijo.attrib[attr].strip():
                    return hijo.attrib[attr].strip()
        for attr in nodo.attrib:
            if compacta(attr) in objetivo and nodo.attrib[attr].strip():
                return nodo.attrib[attr].strip()
        return ""

    for nodo in raiz.iter():
        if nodo is raiz and len(list(raiz)) > 1:
            continue          # la raíz agrupa a todas: no es una estación
        permiso = ""
        for v in list(nodo.attrib.values()):
            m = PERMISO_RE.search(str(v))
            if m:
                permiso = m.group(0)
                break
        if not permiso:
            hijo = texto_de(nodo, ("cre_id", "creid", "permiso", "permiso_cre", "numero", "num_permiso"))
            m = PERMISO_RE.search(hijo or "")
            if m:
                permiso = m.group(0)
        if not permiso:
            continue

        registro = {
            "Place ID": (nodo.get("place_id") or nodo.get("placeId") or "").strip(),
            "Marca": texto_de(nodo, ("marca", "brand", "bandera")),
            "Estacion": texto_de(nodo, ("name", "nombre", "razon_social", "razonsocial", "nombre_comercial")),
            "Direccion": texto_de(nodo, ("address", "direccion", "domicilio", "street", "calle")),
            "Municipio": texto_de(nodo, ("municipio", "municipality", "city", "localidad", "ciudad")),
            "Estado": texto_de(nodo, ("estado", "state", "entidad", "entidad_federativa")),
            "Region": texto_de(nodo, ("region", "zona")),
            "Lat": texto_de(nodo, ("y", "lat", "latitud", "latitude")),
            "Lon": texto_de(nodo, ("x", "lon", "lng", "longitud", "longitude")),
        }
        if not any(registro.values()):
            continue
        idx.setdefault("".join(permiso.split()).upper(), registro)
        idx.setdefault(clave_permiso(permiso), registro)

    return idx


def leer_catalogo(ruta):
    """Indexa el catálogo por permiso literal y por clave canónica.
    Acepta CSV o el XML de estaciones de la CNE."""
    if not ruta:
        return {}
    if not os.path.exists(ruta):
        sys.exit("No se encontró el catálogo: %s" % ruta)
    # Se decide por el contenido, no por la extensión: el archivo descargado
    # del portal a veces llega guardado como .html o sin extensión.
    with open(ruta, "rb") as fh:
        inicio = fh.read(400).lstrip(b"\xef\xbb\xbf").lstrip()
    if ruta.lower().endswith(".xml") or inicio[:1] == b"<":
        return leer_catalogo_xml(ruta)

    idx = {}
    with io.open(ruta, encoding="utf-8-sig", newline="") as fh:
        lector = csv.reader(fh)
        try:
            encabezados = [norm_encabezado(h) for h in next(lector)]
        except StopIteration:
            return idx

        def col(campo):
            for alias in ALIAS_CATALOGO[campo]:
                if alias in encabezados:
                    return encabezados.index(alias)
            return -1

        cols = dict((campo, col(campo)) for campo in ALIAS_CATALOGO)

        if cols["permiso"] < 0:
            sys.exit("El catálogo no tiene columna de permiso (Permiso CRE / Número).")

        def val(fila, campo):
            i = cols[campo]
            if i < 0 or i >= len(fila):
                return ""
            v = (fila[i] or "").strip()
            return "" if v.lower() in ("", "n/a", "n/d", "-", SIN_DATO.lower()) else v

        for fila in lector:
            if not fila or cols["permiso"] >= len(fila):
                continue
            permiso = (fila[cols["permiso"]] or "").strip()
            if not permiso:
                continue
            registro = {
                "Place ID": val(fila, "place_id"),
                "Lat": val(fila, "lat"),
                "Lon": val(fila, "lon"),
                "Marca": val(fila, "marca"),
                "Estacion": val(fila, "estacion"),
                "Direccion": val(fila, "direccion"),
                "Municipio": val(fila, "municipio"),
                "Estado": val(fila, "estado"),
                "Region": val(fila, "region"),
            }
            idx.setdefault("".join(permiso.split()).upper(), registro)
            idx.setdefault(clave_permiso(permiso), registro)
    return idx


def leer_xml(ruta):
    """
    Lee el XML tolerando basura al inicio: un BOM UTF-8, saltos de línea o
    espacios antes de la declaración hacen fallar a ElementTree con
    "not well-formed, line 1, column 0", un error que no dice nada sobre su
    causa real.
    """
    with open(ruta, "rb") as fh:
        datos = fh.read()
    if datos[:3] == b"\xef\xbb\xbf":
        datos = datos[3:]
    datos = datos.lstrip()
    corte = datos.find(b"<")
    if corte > 0:
        datos = datos[corte:]
    try:
        return ET.fromstring(datos)
    except ET.ParseError as e:
        sys.exit("El XML no se pudo interpretar (%s). Primeros bytes: %r" % (e, datos[:80]))


def indexar_por_place_id(catalogo):
    """place_id -> permiso CRE, para cruzar el XML de precios con el catálogo."""
    idx = {}
    for clave, reg in catalogo.items():
        pid = str(reg.get("Place ID") or "").strip()
        if pid and pid not in idx and PERMISO_RE.match(clave or ""):
            idx[pid] = clave
    return idx


def convertir(ruta_xml, catalogo, minimo, maximo, fecha_forzada=""):
    """
    Acepta los dos esquemas que ha publicado la Comisión:

      A) <precios fecha_generacion="AAAA-MM-DD">
           <estacion permiso="PL/.../EXP/ES/AAAA">
             <producto tipo="regular" precio="22.95"/>

      B) <places>                          (el que sirve el endpoint vigente)
           <place place_id="11703">
             <gas_price type="regular">22.95</gas_price>

    El esquema B identifica la estación por place_id, no por permiso: el
    catálogo de estaciones aporta la equivalencia. Tampoco trae fecha, así
    que se toma la del día (o la que se indique con --fecha).
    """
    if not os.path.exists(ruta_xml):
        sys.exit("No se encontró el XML: %s" % ruta_xml)

    raiz = leer_xml(ruta_xml)
    fecha = raiz.get("fecha_generacion", "")
    if not fecha:
        fecha = fecha_forzada or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    registros, orden = {}, []
    st = {"estaciones": 0, "duplicados": 0, "descartados": 0, "sin_catalogo": 0,
          "sin_equivalencia": 0, "esquema": "precios/estacion"}

    nodos = raiz.findall("estacion")
    if not nodos:
        nodos = raiz.findall("place")
        if nodos:
            st["esquema"] = "places/place (place_id)"
            return convertir_places(nodos, catalogo, minimo, maximo, fecha, st)

    for est in nodos:
        permiso = " ".join(str(est.get("permiso") or "").split())
        if not permiso:
            continue
        st["estaciones"] += 1
        clave = clave_permiso(permiso)

        precios = {}
        for prod in est.findall("producto"):
            columna = PRODUCTOS.get((prod.get("tipo") or "").strip().lower())
            if not columna:
                continue
            try:
                valor = float(prod.get("precio"))
            except (TypeError, ValueError):
                continue
            if valor < minimo or valor > maximo:
                st["descartados"] += 1
                continue
            precios[columna] = "%.2f" % valor

        if clave in registros:
            st["duplicados"] += 1
            for columna, v in precios.items():
                if not registros[clave][columna]:
                    registros[clave][columna] = v
            continue

        info = catalogo.get("".join(permiso.split()).upper()) or catalogo.get(clave) or {}
        if not info:
            st["sin_catalogo"] += 1

        fila = {
            "Fecha": fecha,
            "Region": info.get("Region", ""),
            "Estado": info.get("Estado", ""),
            "Municipio": info.get("Municipio", ""),
            "Marca": info.get("Marca", ""),
            "Estacion": info.get("Estacion", ""),
            "Permiso CRE": permiso,
            "Direccion": info.get("Direccion", ""),
            "Regular": precios.get("Regular", ""),
            "Premium": precios.get("Premium", ""),
            "Diesel": precios.get("Diesel", ""),
        }
        for campo in CON_MARCADOR:
            if not fila[campo]:
                fila[campo] = SIN_DATO

        registros[clave] = fila
        orden.append(clave)

    filas = [registros[k] for k in orden]
    st["filas"] = len(filas)
    st["con_catalogo"] = st["filas"] - st["sin_catalogo"]
    st["fecha"] = fecha
    return filas, st


def leer_existente(ruta):
    """Devuelve (filas, fechas) del CSV acumulado, o listas vacías."""
    if not os.path.exists(ruta) or os.path.getsize(ruta) == 0:
        return [], []
    with io.open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    fechas = []
    for f in filas:
        v = (f.get("Fecha") or "").strip()
        if v and v not in fechas:
            fechas.append(v)
    return filas, sorted(fechas)


def convertir_places(nodos, catalogo, minimo, maximo, fecha, st):
    """Esquema B: <place place_id><gas_price type>precio</gas_price>."""
    equivalencia = indexar_por_place_id(catalogo)

    # Sin equivalencias el resultado seria un padron de precios anonimos, sin
    # razon social ni ubicacion: es preferible detenerse y decir por que.
    if not equivalencia:
        sys.exit(
            "El catálogo no trae la columna 'Place ID', que es la llave con la que el XML de\n"
            "precios identifica cada estación. Estás usando un catalogo_estaciones.csv anterior.\n"
            "Regenéralo con:\n"
            "  curl -fsSL -o places.xml \"https://publicacionexterna.azurewebsites.net/publicaciones/places\"\n"
            "  python3 xml_a_csv.py places.xml --catalogo places.xml \\\n"
            "          --exportar-catalogo catalogo_estaciones.csv --salida /dev/null")

    registros, orden = {}, []

    for place in nodos:
        pid = (place.get("place_id") or "").strip()
        if not pid:
            continue
        st["estaciones"] += 1

        permiso = equivalencia.get(pid, "")
        if not permiso:
            # Sin equivalencia el registro no puede identificarse ni ubicarse:
            # se conserva con un identificador propio para no perder el precio.
            st["sin_equivalencia"] += 1
            permiso = "PLACE/" + pid

        precios = {}
        for gp in place.findall("gas_price"):
            columna = PRODUCTOS.get((gp.get("type") or "").strip().lower())
            if not columna:
                continue
            try:
                valor = float((gp.text or "").strip())
            except (TypeError, ValueError):
                continue
            if valor < minimo or valor > maximo:
                st["descartados"] += 1
                continue
            precios[columna] = "%.2f" % valor

        clave = clave_permiso(permiso)
        if clave in registros:
            st["duplicados"] += 1
            for columna, v in precios.items():
                if not registros[clave][columna]:
                    registros[clave][columna] = v
            continue

        info = catalogo.get("".join(permiso.split()).upper()) or catalogo.get(clave) or {}
        if not info:
            st["sin_catalogo"] += 1

        fila = {
            "Fecha": fecha,
            "Region": info.get("Region", ""),
            "Estado": info.get("Estado", ""),
            "Municipio": info.get("Municipio", ""),
            "Marca": info.get("Marca", ""),
            "Estacion": info.get("Estacion", ""),
            "Permiso CRE": permiso,
            "Direccion": info.get("Direccion", ""),
            "Regular": precios.get("Regular", ""),
            "Premium": precios.get("Premium", ""),
            "Diesel": precios.get("Diesel", ""),
        }
        for campo in CON_MARCADOR:
            if not fila[campo]:
                fila[campo] = SIN_DATO

        registros[clave] = fila
        orden.append(clave)

    filas = [registros[k] for k in orden]
    st["filas"] = len(filas)
    st["con_catalogo"] = st["filas"] - st["sin_catalogo"]
    st["fecha"] = fecha
    return filas, st


def escribir(filas, salida, acumular, conservar, fecha):
    """
    Sin --acumular reemplaza el archivo. Con --acumular:
      · si la fecha ya está en el archivo, no vuelve a escribirla;
      · conserva únicamente los últimos `conservar` cortes diarios.
    """
    carpeta = os.path.dirname(salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    if not acumular:
        with io.open(salida, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNAS, lineterminator="\n")
            w.writeheader()
            w.writerows(filas)
        return {"accion": "reemplazado", "periodos": 1, "filas": len(filas)}

    previas, fechas = leer_existente(salida)
    if fecha and fecha in fechas:
        return {"accion": "sin cambios (la fecha ya estaba cargada)",
                "periodos": len(fechas), "filas": len(previas)}

    todas = previas + filas
    fechas = sorted(set(fechas + ([fecha] if fecha else [])))
    if conservar and len(fechas) > conservar:
        vigentes = set(fechas[-conservar:])
        todas = [f for f in todas if (f.get("Fecha") or "").strip() in vigentes]
        fechas = sorted(vigentes)

    with io.open(salida, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for f in todas:
            w.writerow(dict((c, f.get(c, "")) for c in COLUMNAS))
    return {"accion": "acumulado", "periodos": len(fechas), "filas": len(todas)}


def escribir_historico(filas, ruta, fecha, conservar):
    """
    Serie histórica ligera: un renglón por ámbito y producto, no por estación.
    Es lo que alimenta la gráfica de tendencia sin que el repositorio crezca
    decenas de megabytes al día.
    """
    if not ruta or not fecha:
        return None

    acc = {}
    def sumar(ambito, clave, prod, valor):
        k = (ambito, clave, prod)
        if k not in acc:
            acc[k] = [0.0, 0]
        acc[k][0] += valor
        acc[k][1] += 1

    # Ámbitos nacional, estatal y regional. A propósito NO se guarda el nivel
    # municipal: con 1,400 municipios el archivo pasaría de 5 KB a 550 KB por
    # corte, y a 120 cortes serían 33 MB que el navegador tendría que leer en
    # cada carga. Al filtrar un municipio, la tendencia usa su estado.
    for f in filas:
        for prod in ("Regular", "Premium", "Diesel"):
            if not f[prod]:
                continue
            v = float(f[prod])
            sumar("nacional", "MX", prod, v)
            if f["Estado"] and f["Estado"] != SIN_DATO:
                sumar("estado", f["Estado"], prod, v)
            if f.get("Region") and f["Region"] != SIN_DATO:
                sumar("region", f["Region"], prod, v)

    previas, fechas = [], []
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        with io.open(ruta, encoding="utf-8-sig", newline="") as fh:
            previas = list(csv.DictReader(fh))
        fechas = sorted(set((f.get("Fecha") or "").strip() for f in previas if f.get("Fecha")))
        if fecha in fechas:
            return {"accion": "sin cambios", "periodos": len(fechas)}

    nuevas = []
    for (ambito, clave, prod), (total, n) in sorted(acc.items()):
        nuevas.append({"Fecha": fecha, "Ambito": ambito, "Clave": clave,
                       "Producto": prod, "Promedio": "%.4f" % (total / n), "Estaciones": n})

    todas = previas + nuevas
    fechas = sorted(set(fechas + [fecha]))
    if conservar and len(fechas) > conservar:
        vigentes = set(fechas[-conservar:])
        todas = [f for f in todas if (f.get("Fecha") or "").strip() in vigentes]
        fechas = sorted(vigentes)

    with io.open(ruta, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS_HISTORICO, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for f in todas:
            w.writerow(dict((c, f.get(c, "")) for c in COLUMNAS_HISTORICO))
    return {"accion": "actualizado", "periodos": len(fechas), "filas": len(todas)}


COLUMNAS_CATALOGO = ["Permiso CRE", "Place ID", "Marca", "Estacion", "Direccion",
                     "Municipio", "Estado", "Region", "Lat", "Lon"]

# Las 8 regiones de la Política Pública de Almacenamiento Mínimo de Petrolíferos,
# tal como las usa Profeco en "Quién es Quién en los Precios".
REGIONES = {
    "Noroeste": ["Baja California", "Baja California Sur", "Sonora", "Sinaloa", "Nayarit"],
    "Norte": ["Chihuahua", "Durango"],
    "Noreste": ["Coahuila", "Coahuila de Zaragoza", "Nuevo León", "Tamaulipas", "San Luis Potosí"],
    "Occidente": ["Zacatecas", "Aguascalientes", "Jalisco", "Guanajuato", "Michoacán",
                  "Michoacán de Ocampo", "Colima"],
    "Centro": ["Querétaro", "Querétaro de Arteaga", "Hidalgo", "Tlaxcala", "Puebla", "Morelos",
               "México", "Estado de México", "Ciudad de México", "Distrito Federal"],
    "Golfo": ["Veracruz", "Veracruz de Ignacio de la Llave", "Tabasco"],
    "Sur": ["Guerrero", "Oaxaca", "Chiapas"],
    "Sureste": ["Campeche", "Yucatán", "Quintana Roo"],
}

ESTADO_A_REGION = {}
for _reg, _edos in REGIONES.items():
    for _e in _edos:
        ESTADO_A_REGION[_e.lower()] = _reg


def region_de(estado):
    return ESTADO_A_REGION.get((estado or "").strip().lower(), "")


# ---------------------------------------------------------------------------
#  Asignación de estado por coordenadas (punto en polígono)
# ---------------------------------------------------------------------------

def cargar_estados_geojson(ruta):
    """Devuelve [(estado, anillos, bbox)] a partir de un GeoJSON de entidades."""
    import json
    with io.open(ruta, encoding="utf-8") as fh:
        gj = json.load(fh)
    salida = []
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        nombre = ""
        for clave in ("ESTADO", "estado", "NOMBRE", "name", "NOM_ENT", "NAME_1"):
            if props.get(clave):
                nombre = str(props[clave]).strip()
                break
        geo = feat.get("geometry") or {}
        coords = geo.get("coordinates") or []
        if geo.get("type") == "MultiPolygon":
            anillos = [poly[0] for poly in coords if poly]
        elif geo.get("type") == "Polygon":
            anillos = [coords[0]] if coords else []
        else:
            continue
        if not nombre or not anillos:
            continue
        xs = [p[0] for a in anillos for p in a]
        ys = [p[1] for a in anillos for p in a]
        salida.append((nombre, anillos, (min(xs), min(ys), max(xs), max(ys))))
    return salida


# ---------------------------------------------------------------------------
#  Municipios: TopoJSON (arcos cuantizados y en deltas) -> punto en polígono
# ---------------------------------------------------------------------------

def cargar_municipios_topojson(ruta, objeto="municipalities"):
    """
    Decodifica un TopoJSON y devuelve [(municipio, anillos, bbox)].
    Los arcos vienen como incrementos sobre una malla cuantizada: hay que
    acumularlos y aplicar la transformación antes de tener coordenadas reales.
    """
    import json
    with io.open(ruta, encoding="utf-8") as fh:
        topo = json.load(fh)
    if objeto not in (topo.get("objects") or {}):
        return []

    tr = topo.get("transform") or {}
    sx, sy = (tr.get("scale") or [1, 1])
    tx, ty = (tr.get("translate") or [0, 0])

    arcos = []
    for arco in topo.get("arcs", []):
        x = y = 0
        puntos = []
        for par in arco:
            x += par[0]
            y += par[1]
            puntos.append((x * sx + tx, y * sy + ty))
        arcos.append(puntos)

    def linea(indices):
        pts = []
        for i in indices:
            tramo = arcos[~i][::-1] if i < 0 else arcos[i]
            pts.extend(tramo[1:] if pts else tramo)
        return pts

    salida = []
    for g in topo["objects"][objeto].get("geometries", []):
        if g.get("type") == "Polygon":
            anillos = [linea(r) for r in g["arcs"]]
        elif g.get("type") == "MultiPolygon":
            anillos = [linea(poly[0]) for poly in g["arcs"]]
        else:
            continue
        nombre = ""
        props = g.get("properties") or {}
        for clave in ("mun_name", "NOM_MUN", "municipio", "name"):
            if props.get(clave):
                nombre = str(props[clave]).strip()
                break
        if not nombre or not anillos or not anillos[0]:
            continue
        xs = [p[0] for r in anillos for p in r]
        ys = [p[1] for r in anillos for p in r]
        salida.append((nombre, anillos, (min(xs), min(ys), max(xs), max(ys))))
    return salida


def indexar_municipios(municipios, paso=0.5):
    """Rejilla de bounding boxes: evita recorrer 2,400 polígonos por estación."""
    malla = {}
    for k, (_n, _a, bb) in enumerate(municipios):
        for gx in range(int(bb[0] // paso), int(bb[2] // paso) + 1):
            for gy in range(int(bb[1] // paso), int(bb[3] // paso) + 1):
                malla.setdefault((gx, gy), []).append(k)
    return {"paso": paso, "malla": malla}


def municipio_por_coordenadas(x, y, municipios, indice):
    paso = indice["paso"]
    for k in indice["malla"].get((int(x // paso), int(y // paso)), ()):
        nombre, anillos, bb = municipios[k]
        if not (bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]):
            continue
        if _dentro(x, y, anillos[0]):
            hueco = False
            for interior in anillos[1:]:
                if _dentro(x, y, interior):
                    hueco = True
                    break
            if not hueco:
                return nombre
    return ""


def _dentro(x, y, anillo):
    dentro, n = False, len(anillo)
    j = n - 1
    for i in range(n):
        xi, yi = anillo[i][0], anillo[i][1]
        xj, yj = anillo[j][0], anillo[j][1]
        if (yi > y) != (yj > y):
            corte = (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
            if x < corte:
                dentro = not dentro
        j = i
    return dentro


def estado_por_coordenadas(x, y, entidades, tolerancia=0.2):
    """
    Entidad que contiene el punto. Si ninguna lo contiene —típico en estaciones
    costeras, donde el polígono simplificado deja fuera la línea de costa— se
    devuelve la más cercana dentro de `tolerancia` grados (~20 km).
    """
    for nombre, anillos, bb in entidades:
        if not (bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]):
            continue
        for anillo in anillos:
            if _dentro(x, y, anillo):
                return nombre, False
    mejor, mejor_d = "", tolerancia ** 2
    for nombre, anillos, bb in entidades:
        if x < bb[0] - tolerancia or x > bb[2] + tolerancia:
            continue
        if y < bb[1] - tolerancia or y > bb[3] + tolerancia:
            continue
        for anillo in anillos:
            for px, py in anillo:
                d = (px - x) ** 2 + (py - y) ** 2
                if d < mejor_d:
                    mejor_d, mejor = d, nombre
    return (mejor, True) if mejor else ("", False)


def enriquecer_geografia(catalogo, ruta_geojson, ruta_municipios=""):
    """Rellena Estado y Municipio por coordenadas, y Region por tabla oficial."""
    entidades = cargar_estados_geojson(ruta_geojson) if ruta_geojson else []
    municipios, indice = [], None
    if ruta_municipios:
        municipios = cargar_municipios_topojson(ruta_municipios)
        if municipios:
            indice = indexar_municipios(municipios)
    st = {"por_coordenadas": 0, "aproximados": 0, "sin_asignar": 0, "region": 0, "municipios": 0}
    vistos = set()
    for clave, reg in catalogo.items():
        if id(reg) in vistos:
            continue
        vistos.add(id(reg))
        try:
            x = float(reg.get("Lon") or "")
            y = float(reg.get("Lat") or "")
        except ValueError:
            x = y = None

        if not reg.get("Estado") and entidades and x is not None:
            nombre, aprox = estado_por_coordenadas(x, y, entidades)
            if nombre:
                reg["Estado"] = nombre
                st["por_coordenadas"] += 1
                if aprox:
                    st["aproximados"] += 1
            else:
                st["sin_asignar"] += 1
        elif not reg.get("Estado"):
            st["sin_asignar"] += 1

        if not reg.get("Municipio") and indice and x is not None:
            m = municipio_por_coordenadas(x, y, municipios, indice)
            if m:
                reg["Municipio"] = m
                st["municipios"] += 1
        if reg.get("Estado") and not reg.get("Region"):
            r = region_de(reg["Estado"])
            if r:
                reg["Region"] = r
                st["region"] += 1
    return st


def exportar_catalogo(catalogo, ruta):
    """
    Vuelca el catálogo leído (CSV o XML) a un CSV con la estructura que espera
    el tablero. Es la vía para convertir el XML de estaciones de la CNE en tu
    catalogo_estaciones.csv con miles de permisos identificados.
    """
    vistos, filas = set(), []
    for clave, reg in catalogo.items():
        if not PERMISO_RE.match(clave or ""):
            continue                      # se indexa dos veces por permiso
        canon = clave_permiso(clave)
        if canon in vistos:
            continue
        vistos.add(canon)
        filas.append({
            "Permiso CRE": clave,
            "Place ID": reg.get("Place ID", ""),
            "Marca": reg.get("Marca", ""),
            "Estacion": reg.get("Estacion", ""),
            "Direccion": reg.get("Direccion", ""),
            "Municipio": reg.get("Municipio", ""),
            "Estado": reg.get("Estado", ""),
            "Region": reg.get("Region", ""),
            "Lat": reg.get("Lat", ""),
            "Lon": reg.get("Lon", ""),
        })
    filas.sort(key=lambda f: f["Permiso CRE"])

    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    with io.open(ruta, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS_CATALOGO, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)

    con_nombre = sum(1 for f in filas if f["Estacion"])
    con_municipio = sum(1 for f in filas if f["Municipio"])
    con_coords = sum(1 for f in filas if f["Lat"] and f["Lon"])
    return {"filas": len(filas), "nombre": con_nombre,
            "municipio": con_municipio, "coords": con_coords}


COLUMNAS_REPORTE = ["Fecha", "Producto", "Bloque", "Clave", "Estaciones",
                    "Promedio", "Minimo", "Maximo", "Diferencial_vs_minimo",
                    "P25", "Mediana", "P75", "P90",
                    "Estacion_extremo", "Permiso_extremo"]


def percentil(ordenados, q):
    """Percentil por interpolación lineal sobre una lista ya ordenada."""
    if not ordenados:
        return None
    if len(ordenados) == 1:
        return ordenados[0]
    pos = (len(ordenados) - 1) * q
    bajo = int(pos)
    alto = min(bajo + 1, len(ordenados) - 1)
    return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (pos - bajo)


def generar_reporte(filas, ruta, fecha, marcas):
    """
    Métricas homólogas a "Quién es Quién en los Precios" con los datos que sí
    publican la CNE y el SAT:

      · nacional  promedio, mínimo y máximo por producto
      · marca     promedio por marca reconocida y su diferencial
      · region    promedio y extremos en las 8 regiones oficiales

    Nota: Profeco publica el margen de ganancia con estimaciones de la SENER
    (precio de referencia en TAR, IEPS y estímulos) que no vienen en estas
    publicaciones. Aquí se reporta el DIFERENCIAL contra el precio más bajo del
    periodo, que sí es medible, y se etiqueta como tal.
    """
    if not ruta or not fecha:
        return None

    marcas_norm = [(m, " " + " ".join(m.lower().split()) + " ") for m in (marcas or [])]

    def marca_de(fila):
        if fila.get("Marca"):
            return fila["Marca"]
        campo = " " + " ".join((fila.get("Estacion") or "").lower().split()) + " "
        for nombre, frase in marcas_norm:
            if frase in campo:
                return nombre
        return ""

    salida = []
    for prod in ("Regular", "Premium", "Diesel"):
        datos = [(float(f[prod]), f) for f in filas if f[prod]]
        if not datos:
            continue
        datos.sort(key=lambda d: d[0])
        precios = [d[0] for d in datos]
        base = precios[0]
        promedio = sum(precios) / len(precios)

        salida.append({"Fecha": fecha, "Producto": prod, "Bloque": "nacional", "Clave": "MX",
                       "Estaciones": len(precios), "Promedio": "%.4f" % promedio,
                       "Minimo": "%.2f" % base, "Maximo": "%.2f" % precios[-1],
                       "Diferencial_vs_minimo": "%.2f" % (promedio - base),
                       "P25": "%.2f" % percentil(precios, 0.25),
                       "Mediana": "%.2f" % percentil(precios, 0.50),
                       "P75": "%.2f" % percentil(precios, 0.75),
                       "P90": "%.2f" % percentil(precios, 0.90),
                       "Estacion_extremo": datos[-1][1].get("Estacion", ""),
                       "Permiso_extremo": datos[-1][1].get("Permiso CRE", "")})

        por_marca, por_region = {}, {}
        for precio, f in datos:
            m = marca_de(f)
            if m:
                por_marca.setdefault(m, []).append((precio, f))
            reg = f.get("Region") or ""
            if reg and reg != SIN_DATO:
                por_region.setdefault(reg, []).append((precio, f))

        for bloque, grupos in (("marca", por_marca), ("region", por_region)):
            for clave in sorted(grupos):
                g = grupos[clave]
                pr = [x[0] for x in g]
                media = sum(pr) / len(pr)
                salida.append({"Fecha": fecha, "Producto": prod, "Bloque": bloque, "Clave": clave,
                               "Estaciones": len(pr), "Promedio": "%.4f" % media,
                               "Minimo": "%.2f" % pr[0], "Maximo": "%.2f" % pr[-1],
                               "Diferencial_vs_minimo": "%.2f" % (media - base),
                               "P25": "%.2f" % percentil(pr, 0.25),
                               "Mediana": "%.2f" % percentil(pr, 0.50),
                               "P75": "%.2f" % percentil(pr, 0.75),
                               "P90": "%.2f" % percentil(pr, 0.90),
                               "Estacion_extremo": g[-1][1].get("Estacion", ""),
                               "Permiso_extremo": g[-1][1].get("Permiso CRE", "")})

    previas = []
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        with io.open(ruta, encoding="utf-8-sig", newline="") as fh:
            previas = [f for f in csv.DictReader(fh) if (f.get("Fecha") or "").strip() != fecha]

    with io.open(ruta, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS_REPORTE, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for f in previas + salida:
            w.writerow(dict((c, f.get(c, "")) for c in COLUMNAS_REPORTE))
    return {"filas": len(salida), "total": len(previas) + len(salida)}


def main():
    ap = argparse.ArgumentParser(
        description="Convierte el XML oficial de precios de la CNE al CSV del tablero.")
    ap.add_argument("xml", help="Archivo XML descargado del portal de la CNE")
    ap.add_argument("--catalogo", default="catalogo_estaciones.csv",
                    help="Catálogo permiso → razón social, dirección y ubicación (por omisión catalogo_estaciones.csv)")
    ap.add_argument("--salida", default="fallback.csv",
                    help="CSV de salida (por omisión fallback.csv, que es lo que lee config.js)")
    ap.add_argument("--acumular", action="store_true",
                    help="Agrega el periodo al archivo en lugar de reemplazarlo (no duplica fechas ya cargadas)")
    ap.add_argument("--conservar", type=int, default=0,
                    help="Con --acumular, número de cortes diarios a conservar (0 = todos)")
    ap.add_argument("--historico", default="",
                    help="CSV de promedios diarios por ámbito y producto que alimenta la gráfica de tendencia")
    ap.add_argument("--historico-conservar", type=int, default=120,
                    help="Cortes diarios a conservar en el histórico de promedios (por omisión 120)")
    ap.add_argument("--exportar-catalogo", default="",
                    help="Escribe el catálogo leído a este CSV (útil para convertir el XML de estaciones de la CNE)")
    ap.add_argument("--reporte", default="",
                    help="CSV con las métricas estilo Profeco (nacional, por marca y por región)")
    ap.add_argument("--marcas", default="BP,TOTALENERGIES,REPSOL,SHELL,CHEVRON,EXXONMOBIL,GULF,G500,OXXO GAS,ARCO NORTE",
                    help="Marcas a reconocer en el reporte, separadas por coma")
    ap.add_argument("--geojson", default="",
                    help="GeoJSON de las 32 entidades para deducir Estado de las coordenadas del catálogo")
    ap.add_argument("--municipios", default="",
                    help="TopoJSON de municipios para deducir Municipio de las coordenadas del catálogo")
    ap.add_argument("--fecha", default="",
                    help="Fecha del corte AAAA-MM-DD cuando el XML no la trae (por omisión, la de hoy en UTC)")
    ap.add_argument("--min", type=float, default=15.0, help="Precio mínimo válido (por omisión 15.00)")
    ap.add_argument("--max", type=float, default=45.0, help="Precio máximo válido (por omisión 45.00)")
    args = ap.parse_args()

    catalogo = leer_catalogo(args.catalogo if os.path.exists(args.catalogo) else "")
    if args.catalogo and not catalogo:
        print("Aviso: no se cargó catálogo; las estaciones quedarán identificadas por su permiso.")

    if args.geojson or args.municipios:
        g = enriquecer_geografia(catalogo, args.geojson, args.municipios)
        print("Estados por coordenadas:  %d (%d aproximados por cercanía) · %d sin asignar · %d con región"
              % (g["por_coordenadas"], g["aproximados"], g["sin_asignar"], g["region"]))
        if g["municipios"]:
            print("Municipios por polígono:  %d" % g["municipios"])

    if args.exportar_catalogo:
        ce = exportar_catalogo(catalogo, args.exportar_catalogo)
        print("Catálogo exportado:       %s (%d permisos · %d con nombre · %d con municipio · %d con coordenadas)"
              % (args.exportar_catalogo, ce["filas"], ce["nombre"], ce["municipio"], ce["coords"]))

    filas, st = convertir(args.xml, catalogo, args.min, args.max, args.fecha)
    if not filas:
        sys.exit("El XML no produjo filas.")
    res = escribir(filas, args.salida, args.acumular, args.conservar, st["fecha"])
    hist = escribir_historico(filas, args.historico, st["fecha"], args.historico_conservar)

    print("Esquema detectado:        %s" % st.get("esquema", "precios/estacion"))
    print("Fecha del corte:          %s" % st["fecha"])
    print("Estaciones en el XML:     %d" % st["estaciones"])
    if st.get("sin_equivalencia"):
        print("Sin equivalencia:         %d place_id que no están en el catálogo" % st["sin_equivalencia"])
    print("Filas escritas:           %d" % st["filas"])
    print("Permisos repetidos:       %d (fusionados con el primer registro)" % st["duplicados"])
    print("Precios fuera de rango:   %d (descartados, límites %.2f-%.2f)" % (st["descartados"], args.min, args.max))
    print("Con datos de catálogo:    %d de %d" % (st["con_catalogo"], st["filas"]))
    print("Archivo:                  %s (%s · %d periodo(s) · %d filas)" %
          (args.salida, res["accion"], res["periodos"], res["filas"]))
    if hist:
        print("Histórico de promedios:   %s (%s · %d periodo(s))" %
              (args.historico, hist["accion"], hist["periodos"]))

    if args.reporte:
        rep_ = generar_reporte(filas, args.reporte, st["fecha"],
                               [m.strip() for m in args.marcas.split(",") if m.strip()])
        if rep_:
            print("Reporte de mercado:       %s (%d renglones del periodo · %d en total)"
                  % (args.reporte, rep_["filas"], rep_["total"]))


if __name__ == "__main__":
    main()
