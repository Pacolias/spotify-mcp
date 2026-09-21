# spotify-mcp

Servidor MCP (Model Context Protocol) para interactuar con la API de Spotify.

## Cómo trabajar en este proyecto

- **El usuario no sabe nada de MCP y está aprendiendo mientras construimos el proyecto.** Cada vez que se introduzca un concepto nuevo de MCP (o de las tecnologías que usemos), hay que explicar los fundamentos: qué es, para qué sirve, cómo encaja con lo que ya existe. No dar nada por sabido. No asumir que "ya se explicó una vez" es suficiente si vuelve a aparecer en un contexto distinto.
- **Ninguna decisión de arquitectura se toma en silencio.** Elección de librerías, estructura de carpetas, patrones de diseño, cómo se maneja la autenticación con Spotify, cómo se exponen las tools/resources del MCP, etc. — todo eso se discute con el usuario antes de implementarlo. Nada de decidir por mi cuenta y presentar el resultado ya hecho.
- **Commits atómicos.** Cada commit debe corresponder a una sola cosa (una feature pequeña, un fix, un paso concreto). Nada de commits gigantes que mezclen varios cambios sin relación.
- **`README.md` como diario de ingeniería, en inglés.** Todas las decisiones importantes (de arquitectura y de cualquier otro tipo) se van documentando ahí, según se toman — está pensado para que lo lea un Tech Lead evaluando el proyecto. Se actualiza de forma continua, no al final.

## Stack

- **Python + FastAPI** como base del proyecto.
- Tecnologías estándar y actuales del ecosistema de desarrollo de IA (a decidir/discutir según se necesiten: cliente de Spotify, gestión de dependencias, etc.) — cada elección se discute primero, ver arriba.

## Decisiones de arquitectura tomadas

Este proyecto es de **portfolio**: pensado para que un Tech Lead pueda evaluarlo fácilmente (idealmente desplegado, sin setup local).

- **Transporte MCP: streamable HTTP** (no stdio). Elegido para poder desplegarlo y que se evalúe sin instalar nada localmente. Pendiente: definir una capa de auth propia para el servidor MCP (aparte del OAuth de Spotify), ya que al ser accesible por red cualquiera podría intentar hablarle.
- **SDK de MCP: SDK oficial de Python** (`mcp`, con `FastMCP`), montado como app ASGI dentro de la app de FastAPI.
- **Auth con Spotify: OAuth2, flujo Authorization Code + PKCE.** El endpoint de callback vive como una ruta más dentro de la misma app FastAPI (el paso de consentimiento pasa por navegador sí o sí, independientemente del transporte MCP).
- **Almacenamiento de tokens: base de datos, SQLite para empezar.** Preferido sobre un fichero JSON plano por persistencia entre reinicios/redeploys y porque demuestra mejor práctica; fácil de migrar a Postgres después.
