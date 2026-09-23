# spotify-mcp

Servidor MCP (Model Context Protocol) para interactuar con la API de Spotify.

## Cómo trabajar en este proyecto

- **El usuario no sabe nada de MCP y está aprendiendo mientras construimos el proyecto.** Cada vez que se introduzca un concepto nuevo de MCP (o de las tecnologías que usemos), hay que explicar los fundamentos: qué es, para qué sirve, cómo encaja con lo que ya existe. No dar nada por sabido. No asumir que "ya se explicó una vez" es suficiente si vuelve a aparecer en un contexto distinto.
- **Modo aprendizaje para todo lo que sea MCP e IA.** El usuario quiere dominar estos temas para trabajar de ello, no solo tener el código hecho. En código que toque MCP (tools, resources, prompts, transporte, protocolo) o IA/LLMs (tool calling, prompts, evals, agentes...): no escribir la solución directamente. Primero explicar el concepto y dar pistas, dejar que el usuario lo escriba, y después revisar su código como en un code review (qué está bien, qué falla, por qué). Solo dar el código completo si el usuario lo pide explícitamente. Boilerplate, tooling y config que no sean de MCP/IA sí se pueden implementar directamente.
- **Ninguna decisión de arquitectura se toma en silencio.** Elección de librerías, estructura de carpetas, patrones de diseño, cómo se maneja la autenticación con Spotify, cómo se exponen las tools/resources del MCP, etc. — todo eso se discute con el usuario antes de implementarlo. Nada de decidir por mi cuenta y presentar el resultado ya hecho.
- **Commits atómicos.** Cada commit debe corresponder a una sola cosa (una feature pequeña, un fix, un paso concreto). Nada de commits gigantes que mezclen varios cambios sin relación.
- **Diario de ingeniería en `journal/`, en inglés.** Todas las decisiones importantes (de arquitectura y de cualquier otro tipo) se documentan como una entrada nueva ahí — un `.md` por entrada, numerado (`01-`, `02-`...) para mantener el orden cronológico, enlazado desde `journal/README.md`. Se añade una entrada según se toma la decisión, no al final. `README.md` (raíz) es distinto: contiene la descripción del proyecto, "How it works" y "Setup" — el punto de entrada para un Tech Lead, no el histórico de decisiones.
- **Push periódico a `origin` en puntos estables.** No hace falta pedir permiso cada vez: cuando se llega a un punto estable (algo que funciona de extremo a extremo, ya probado), se puede hacer `git push` sin preguntar primero. No es "cada commit", es de vez en cuando, en checkpoints con sentido.

## Stack

- **Python + FastAPI** como base del proyecto.
- Tecnologías estándar y actuales del ecosistema de desarrollo de IA (a decidir/discutir según se necesiten: cliente de Spotify, gestión de dependencias, etc.) — cada elección se discute primero, ver arriba.

## Decisiones de arquitectura tomadas

Este proyecto es de **portfolio**.

- **Dirección: servidor MCP remoto, sin monetización** (decidido el 2026-09-23, journal 40). Se migrará de stdio a **streamable HTTP + autorización OAuth de MCP** (el usuario pulsa "conectar" en Claude, no recibe una API key), para el usuario y hasta 4 personas más. **Sin pagos, sin Stripe, sin SaaS público**: Spotify limita las apps en Development Mode a 5 usuarios (el dueño necesita Premium), el Extended Quota exige empresa registrada y 250k MAU, y su Developer Policy prohíbe monetizar apps de reproducción e "ingerir contenido de Spotify en un modelo de IA". Motivo de hacerlo remoto igualmente: valor de portfolio/aprendizaje (así se construyen los connectors MCP reales). Después: vídeo de demo en el README y evals. **El diseño de la implementación (OAuth, hosting, base de datos, rate limits) está pendiente de discutir antes de escribir código.**
- **Transporte MCP actual: stdio** (hasta que se haga la migración de arriba). Decidido el 2026-09-21 (journal 17), revirtiendo el HTTP original; eso descartó el plan de Render y la auth por bearer token, que no se recuperan: la versión remota parte de cero con la OAuth de la spec MCP.
- **SDK de MCP: SDK oficial de Python** (`mcp`, con `MCPServer`, la API de alto nivel — en versiones nuevas del SDK renombrada desde `FastMCP`).
- **Auth con Spotify: OAuth2, flujo Authorization Code + PKCE.** El callback sigue necesitando un servidor HTTP local (navegador de por medio), independientemente del transporte MCP — por eso vive en una app FastAPI aparte (`spotify_mcp.main`), separada del proceso del servidor MCP en sí (`spotify_mcp.stdio_server`).
- **Almacenamiento de tokens: base de datos, SQLite.** Compartida por ambos procesos (login y servidor MCP). Si se mantiene SQLite o se pasa a Postgres en la versión remota está **pendiente de discutir** (depende del hosting).
