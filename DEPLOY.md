# 🚀 Guía de Deploy: Ítaca OS 2.0 en Streamlit Cloud + Turso

## Paso 1: Crear la base de datos en Turso (5 minutos)

### 1.1 Crear cuenta gratuita
1. Ve a [turso.tech](https://turso.tech) y regístrate (gratis, sin tarjeta).

### 1.2 Instalar la CLI de Turso
```bash
# macOS / Linux
curl -sSfL https://get.tur.so/install.sh | bash

# Windows (PowerShell)
iwr https://get.tur.so/install.ps1 -useb | iex
```

### 1.3 Login y crear la base de datos
```bash
turso auth login
turso db create itaca-os
```

### 1.4 Obtener las credenciales
```bash
# URL de la base de datos
turso db show itaca-os --url
# Resultado: libsql://itaca-os-TUNOMBRE.turso.io

# Token de autenticación
turso db tokens create itaca-os
# Resultado: eyJhbGciOi... (un token largo)
```

**Guarda estos dos valores**, los necesitarás en el paso 3.

---

## Paso 2: Subir el código a GitHub (3 minutos)

1. Crea un repositorio nuevo en [github.com](https://github.com/new)
   - Nombre: `itaca-os` (o el que prefieras)
   - Puede ser **privado**

2. Sube todos los archivos del proyecto:
```bash
cd itaca_os_unificado
git init
git add .
git commit -m "Ítaca OS 2.0 - deploy inicial"
git remote add origin https://github.com/TU_USUARIO/itaca-os.git
git push -u origin main
```

---

## Paso 3: Deploy en Streamlit Cloud (5 minutos)

### 3.1 Conectar tu cuenta
1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Inicia sesión con tu cuenta de GitHub

### 3.2 Crear la app
1. Click en **"New app"**
2. Selecciona tu repositorio `itaca-os`
3. Branch: `main`
4. Main file path: `app.py`

### 3.3 Configurar los Secrets (IMPORTANTE)
Antes de hacer deploy, haz click en **"Advanced settings"** y en la sección **Secrets**, pega esto:

```toml
TURSO_DATABASE_URL = "libsql://itaca-os-TUNOMBRE.turso.io"
TURSO_AUTH_TOKEN = "eyJhbGciOi..."
```

Reemplaza con los valores reales del paso 1.4.

4. Click en **"Deploy!"**

---

## Paso 4: Verificar

Tu app estará disponible en:
```
https://TU_USUARIO-itaca-os-app-XXXXX.streamlit.app
```

La primera vez que cargue:
- Se creará la estructura de 31 tablas automáticamente
- Se insertarán los 90 colaboradores de seed data
- Se cargarán los planes estratégicos, sprints y cursos Play

### Credenciales de acceso
- **Email Admin**: `mirai.coronado@itaca.com`
- **Contraseña**: `Itaca2026!`

---

## Desarrollo Local (opcional)

Para correr en tu máquina sin Turso (usa SQLite local automáticamente):

```bash
pip install -r requirements.txt
streamlit run app.py
```

Si no defines `TURSO_DATABASE_URL`, el sistema usa SQLite local en `data/itaca.db`.

Para conectar a Turso localmente:
```bash
export TURSO_DATABASE_URL="libsql://itaca-os-TUNOMBRE.turso.io"
export TURSO_AUTH_TOKEN="eyJhbGciOi..."
streamlit run app.py
```

---

## Troubleshooting

| Problema | Solución |
|---|---|
| "No module named libsql_experimental" | Verificar que `libsql-experimental>=0.0.50` está en `requirements.txt` |
| "Error de autenticación Turso" | Revisar que el token en Secrets no tenga espacios extra |
| La app se ve pero sin datos | Verificar que la URL de Turso es correcta (debe empezar con `libsql://`) |
| Funciona local pero no en Cloud | Revisar los Secrets en Streamlit Cloud (Advanced Settings) |

---

## Arquitectura

```
┌─────────────────────┐     ┌──────────────────┐
│  Streamlit Cloud    │────▶│  Turso Cloud     │
│  (tu app Python)    │     │  (SQLite en nube) │
│  share.streamlit.io │◀────│  turso.io        │
└─────────────────────┘     └──────────────────┘
         │                           │
    Código desde              Base de datos
     GitHub repo              persistente (5GB)
                              gratis para siempre
```
