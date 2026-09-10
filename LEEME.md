# Britzen — código fuente del sitio (versión CMS)

## Qué es cada carpeta
- `content/productos/` → un archivo `.md` por producto (SKU, título, categoría,
  precio, código de Mercado Libre, fotos y descripción completa). Esto es lo
  que edita el panel de administración.
- `assets/` → CSS, JS, logo, y las fotos de producto ya cargadas.
- `admin/` → el panel de Decap CMS (`config.yml` tiene que completarse con el
  nombre real del repositorio de GitHub y la URL del proxy de autenticación).
- `build.py` → arma el sitio completo (lee `content/productos/`, genera
  `dist/` con todas las páginas listas para publicar).

## Cómo se genera el sitio
Cloudflare corre esto automáticamente en cada cambio:
```
pip install -r requirements.txt
python3 build.py
```
La carpeta de salida es `dist/`.

## Pendiente de completar en admin/config.yml
- `repo:` → poner `usuario-de-github/nombre-del-repositorio`
- `base_url:` → poner la URL del OAuth proxy (Cloudflare Worker) una vez desplegado
