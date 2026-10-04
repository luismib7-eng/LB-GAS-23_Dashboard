/* =============================================================
   LB GAS 23 · Service Worker

   Estrategia por tipo de recurso:

     · Cascarón (HTML, CSS, JS, iconos, librerías locales)
         stale-while-revalidate. Se sirve al instante desde la caché y
         se revalida en segundo plano; si la versión cambió, el tablero
         avisa con un botón en lugar de recargar por su cuenta.

     · Datos (CSV, XML, GeoJSON, TopoJSON y cualquier origen externo)
         network-first con respaldo de caché. Nunca se muestra un precio
         viejo teniendo red; sin red, se muestra el último corte guardado
         y el propio tablero declara que es una copia.

     · Mosaicos del mapa
         cache-first con tope de piezas, para no llenar el disco.

   Para publicar una versión nueva, sube VERSION: la caché anterior se
   borra al activar y a las pestañas abiertas les llega el aviso.
   ============================================================= */

var VERSION = "lbgas23-v2";
var CACHE_SHELL = VERSION + "-cascaron";
var CACHE_DATOS = VERSION + "-datos";
var CACHE_MAPA = VERSION + "-mapa";
var MAX_MOSAICOS = 300;

var CASCARON = [
  "./",
  "./index.html",          // CSS, librerias y aplicacion van embebidos aqui
  "./manifest.json",
  "./favicon.png",
  "./apple-touch-icon.png",
  "./icono-192.png",
  "./icono-512.png"
];

var ES_DATO = /\.(csv|xml|geojson|topojson|json)(\?|$)/i;

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE_SHELL).then(function (c) {
      // addAll falla completo si un archivo no está: se agregan uno por uno.
      return Promise.all(CASCARON.map(function (u) {
        return c.add(u).catch(function () { return null; });
      }));
    })
    /* Sin skipWaiting aquí a propósito: el worker nuevo se queda en espera
       hasta que el usuario acepte el aviso. Si tomara control de inmediato,
       una pestaña abierta seguiría ejecutando el JS viejo mientras recibe
       archivos nuevos, que es la forma más silenciosa de romper un tablero. */
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (llaves) {
      /* Se borra todo lo que no pertenezca a esta versión, incluidas las
         cachés de datos y mapa que el worker anterior haya alcanzado a
         crear entre el aviso y la activación. */
      return Promise.all(llaves.map(function (k) {
        return k.indexOf(VERSION + "-") === 0 ? null : caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("message", function (e) {
  // El usuario aceptó: el worker toma control y la página se recarga sola
  // al recibir controllerchange.
  if (e.data === "aplicar-actualizacion") self.skipWaiting();
});

function recortarCache(nombre, tope) {
  caches.open(nombre).then(function (c) {
    c.keys().then(function (llaves) {
      if (llaves.length <= tope) return;
      for (var i = 0; i < llaves.length - tope; i++) c.delete(llaves[i]);
    });
  });
}

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;

  var url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.protocol.indexOf("http") !== 0) return;

  // Mosaicos del mapa: primero caché, con tope de piezas guardadas.
  if (/tile\.openstreetmap\.org/.test(url.hostname)) {
    e.respondWith(
      caches.open(CACHE_MAPA).then(function (c) {
        return c.match(req).then(function (hit) {
          if (hit) return hit;
          return fetch(req).then(function (res) {
            if (res && res.status === 200) {
              c.put(req, res.clone());
              recortarCache(CACHE_MAPA, MAX_MOSAICOS);
            }
            return res;
          }).catch(function () { return hit || Response.error(); });
        });
      })
    );
    return;
  }

  // Datos: primero red; sin red, el último corte guardado.
  if (ES_DATO.test(url.pathname) || url.origin !== self.location.origin) {
    e.respondWith(
      fetch(req).then(function (res) {
        if (res && res.status === 200 && url.origin === self.location.origin) {
          var copia = res.clone();
          caches.open(CACHE_DATOS).then(function (c) { c.put(req, copia); });
        }
        return res;
      }).catch(function () {
        // El parámetro anticaché cambia en cada carga: se ignora al buscar.
        return caches.match(req, { ignoreSearch: true }).then(function (hit) {
          return hit || Response.error();
        });
      })
    );
    return;
  }

  // Cascarón: caché inmediata y revalidación en segundo plano.
  e.respondWith(
    caches.open(CACHE_SHELL).then(function (c) {
      return c.match(req, { ignoreSearch: true }).then(function (hit) {
        var red = fetch(req).then(function (res) {
          if (res && res.status === 200) c.put(req, res.clone());
          return res;
        }).catch(function () { return hit; });
        return hit || red;
      });
    })
  );
});
