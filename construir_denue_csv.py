#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera denue.csv: enriquecimiento por permiso para el tablero."""
import csv, io, math, re, unicodedata
from collections import defaultdict, Counter
DEN="/home/claude/denue_raw/INEGI_DENUE_16102026.csv"
CAT="/home/claude/mision/catalogo_estaciones.csv"
PAD="/home/claude/mision/fallback.csv"
TOL=0.15   # 150 m

def clave(p):
    k=re.sub(r"\s+","",str(p or "").upper()); return k[4:] if k.startswith("CNE/") else k
def nrm(s):
    s=unicodedata.normalize("NFD",str(s or "")).encode("ascii","ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+"," ",s).strip()
def num(v):
    try:
        f=float(str(v).strip()); return f if math.isfinite(f) else None
    except (TypeError,ValueError): return None
def dkm(a,b):
    R,P=6371.0,math.pi/180
    dla,dlo=(b[0]-a[0])*P,(b[1]-a[1])*P
    h=math.sin(dla/2)**2+math.cos(a[0]*P)*math.cos(b[0]*P)*math.sin(dlo/2)**2
    return 2*R*math.asin(min(1.0,math.sqrt(h)))

GENERICO = re.compile(r"COMERCIO AL POR MENOR DE GASOLINA", re.I)

# El archivo del INEGI trae 4 registros (de 14,130) donde una vocal acentuada
# se perdio en la codificacion de origen y quedo como "?". No es un problema de
# lectura: los bytes "?" estan en el archivo descargado.
#
# Se corrigen UNO POR UNO y enumerados, nunca con una regla general, para que
# cualquiera pueda verificar las cuatro. Inventar la letra con una heuristica
# seria rellenar un dato, que es justo lo que no se hace en este proyecto.
ERRATAS_INEGI = [
    ("LUIS F. GARC?A JIMENEZ",   "LUIS F. GARCIA JIMENEZ"),
    ("SANTA MAR?A TEQUEPEXPAN",  "SANTA MARIA TEQUEPEXPAN"),
    ("TEHUAC?N SURFEDERAL",      "TEHUACAN SURFEDERAL"),
    ("GENERALA?NGEL FLORES",     "GENERAL ANGEL FLORES"),
]
def corregir(t):
    for mal, bien in ERRATAS_INEGI:
        if mal in t: t = t.replace(mal, bien)
    return t

D=[]
with io.open(DEN,encoding="latin-1",newline="") as h:
    for x in csv.DictReader(h):
        la,lo=num(x["Latitud"]),num(x["Longitud"])
        if la is None or lo is None: continue
        com=(x["Nombre de la Unidad Económica"] or "").strip()
        rs=(x["Razón social"] or "").strip()
        # El DENUE usa el nombre de la clase cuando el establecimiento no declaró
        # nombre. Eso no es un nombre comercial: se descarta.
        if GENERICO.search(com): com = rs if rs and not GENERICO.search(rs) else ""
        calle=" ".join(filter(None,[x["Tipo de vialidad"],x["Nombre de la vialidad"],
                                    x["Número exterior o kilómetro"]])).strip()
        col=(x["Nombre de asentamiento humano"] or "").strip()
        tipo_col=(x["Tipo de asentamiento humano"] or "").strip()
        dirc=", ".join(filter(None,[calle,
              (tipo_col.title()+" "+col).strip() if col else "",
              (x["Municipio"] or "").strip()]))
        D.append({"la":la,"lo":lo,"com":com,"dir":dirc,
                  "cp":(x["Código Postal"] or "").strip(),
                  "personal":(x["Descripcion estrato personal ocupado"] or "").strip()})

C=0.02; g=defaultdict(list)
for i,d in enumerate(D): g[(int(d["la"]/C),int(d["lo"]/C))].append(i)

cat={}
with io.open(CAT,encoding="utf-8-sig",newline="") as h:
    for r in csv.DictReader(h): cat[clave(r["Permiso CRE"])]=r
with io.open(PAD,encoding="utf-8-sig",newline="") as h: F=list(csv.DictReader(h))
corte=max(x["Fecha"] for x in F)
permisos={}
for x in F:
    if x["Fecha"]!=corte: continue
    permisos[clave(x["Permiso CRE"])]=x["Permiso CRE"]

filas=[]; sinc=0
for k,orig in permisos.items():
    c=cat.get(k)
    if not c: continue
    la,lo=num(c["Lat"]),num(c["Lon"])
    if la is None or lo is None: sinc+=1; continue
    gx,gy=int(la/C),int(lo/C); mejor,md=None,9e9
    for dx in(-1,0,1):
        for dy in(-1,0,1):
            for j in g.get((gx+dx,gy+dy),()):
                d=D[j]; dd=dkm((la,lo),(d["la"],d["lo"]))
                if dd<md: mejor,md=d,dd
    if not mejor or md>TOL: continue
    if not (mejor["com"] or mejor["dir"]): continue
    filas.append({"Permiso CRE":orig,"Nombre comercial":corregir(mejor["com"]),
                  "Direccion":corregir(mejor["dir"]),"CP":mejor["cp"],
                  "Personal":mejor["personal"],"Metros":int(round(md*1000))})

with io.open("denue.csv","w",encoding="utf-8",newline="") as h:
    w=csv.DictWriter(h,fieldnames=["Permiso CRE","Nombre comercial","Direccion","CP","Personal","Metros"])
    w.writeheader(); w.writerows(filas)

T=len(permisos)
cn=sum(1 for f in filas if f["Nombre comercial"])
cd=sum(1 for f in filas if f["Direccion"])
print("Estaciones en el corte %s        : %d" % (corte,T))
print("Cruzadas con el DENUE a <=150 m  : %d  (%.1f%%)" % (len(filas),100.0*len(filas)/T))
print("   ganan nombre comercial        : %d  (%.1f%%)" % (cn,100.0*cn/T))
print("   ganan direccion de calle      : %d  (%.1f%%)" % (cd,100.0*cd/T))
print()
print("denue.csv escrito: %d filas, %d KB" % (len(filas), __import__("os").path.getsize("denue.csv")//1024))
print()
print("Muestra:")
for f in filas[:5]:
    print("   %-22s | %-30s | %s" % (f["Permiso CRE"], f["Nombre comercial"][:30], f["Direccion"][:46]))
