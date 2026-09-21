# spotify-mcp

Servidor MCP (Model Context Protocol) para interactuar con la API de Spotify.

## Cómo trabajar en este proyecto

- **El usuario no sabe nada de MCP y está aprendiendo mientras construimos el proyecto.** Cada vez que se introduzca un concepto nuevo de MCP (o de las tecnologías que usemos), hay que explicar los fundamentos: qué es, para qué sirve, cómo encaja con lo que ya existe. No dar nada por sabido. No asumir que "ya se explicó una vez" es suficiente si vuelve a aparecer en un contexto distinto.
- **Ninguna decisión de arquitectura se toma en silencio.** Elección de librerías, estructura de carpetas, patrones de diseño, cómo se maneja la autenticación con Spotify, cómo se exponen las tools/resources del MCP, etc. — todo eso se discute con el usuario antes de implementarlo. Nada de decidir por mi cuenta y presentar el resultado ya hecho.
- **Commits atómicos.** Cada commit debe corresponder a una sola cosa (una feature pequeña, un fix, un paso concreto). Nada de commits gigantes que mezclen varios cambios sin relación.
- **Diario de ingeniería en `journal/`, en inglés.** Todas las decisiones importantes (de arquitectura y de cualquier otro tipo) se documentan como una entrada nueva ahí — un `.md` por entrada, numerado (`01-`, `02-`...) para mantener el orden cronológico, enlazado desde `journal/README.md`. Se añade una entrada según se toma la decisión, no al final. `README.md` (raíz) es distinto: contiene la descripción del proyecto, "How it works" y "Setup" — el punto de entrada para un Tech Lead, no el histórico de decisiones.
- **Push periódico a `origin` en puntos estables.** No hace falta pedir permiso cada vez: cuando se llega a un punto estable (algo que funciona de extremo a extremo, ya probado), se puede hacer `git push` sin preguntar primero. No es "cada commit", es de vez en cuando, en checkpoints con sentido.

## Stack

- **Python + FastAPI** como base del proyecto.
- Tecnologías estándar y actuales del ecosistema de desarrollo de IA (a decidir/discutir según se necesiten: cliente de Spotify, gestión de dependencias, etc.) — cada elección se discute primero, ver arriba.

## Decisiones de arquitectura tomadas

Este proyecto es de **portfolio**.

- **Transporte MCP: stdio** (no HTTP). Decisión revertida el 2026-09-21 — originalmente era streamable HTTP, pensado para desplegarlo y que un Tech Lead lo evaluara sin setup local; se cambió a stdio para que sea una herramienta puramente local, lanzada como subproceso por el host MCP (Claude Desktop/Code). Trade-off asumido conscientemente: ya no se puede evaluar sin clonar el repo y ejecutarlo. Esto invalidó el plan de despliegue en Render y la auth por bearer token del endpoint MCP (ya no hace falta, stdio no tiene exposición de red).
- **SDK de MCP: SDK oficial de Python** (`mcp`, con `MCPServer`, la API de alto nivel — en versiones nuevas del SDK renombrada desde `FastMCP`).
- **Auth con Spotify: OAuth2, flujo Authorization Code + PKCE.** El callback sigue necesitando un servidor HTTP local (navegador de por medio), independientemente del transporte MCP — por eso vive en una app FastAPI aparte (`spotify_mcp.main`), separada del proceso del servidor MCP en sí (`spotify_mcp.stdio_server`).
- **Almacenamiento de tokens: base de datos, SQLite.** Compartida por ambos procesos (login y servidor MCP). Ya no hay plan de migrar a Postgres (eso era parte del plan de despliegue, descartado).
