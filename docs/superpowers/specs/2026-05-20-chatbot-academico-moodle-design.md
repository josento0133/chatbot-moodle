# Chatbot de Apoyo Académico para Moodle — Especificación de Diseño

**Fecha:** 2026-05-20
**Estado:** Aprobado

---

## Contexto y Objetivo

Desarrollar un chatbot inteligente integrado nativamente en Moodle que ayude a estudiantes de Bachillerato (16-18 años) a resolver dudas académicas en tiempo real, proponer ejercicios de práctica y hacer seguimiento de su progreso. El chatbot funciona fuera del horario escolar y se adapta al ritmo de cada estudiante.

**Materias cubiertas:** Matemáticas, Física, Lengua, Literatura, Inglés, Química, Biología, Historia y Ciencias Sociales.

---

## Arquitectura General

El sistema tiene tres capas que se comunican entre sí:

```
Moodle (PHP Plugin - block_chatbot)
        ↕  REST API (JSON + JWT)
Python FastAPI Backend
        ↕  HTTP local
Ollama  →  Llama 3 / Mistral (LLM local)
```

- **Plugin Moodle (`block_chatbot`):** Bloque que aparece en el sidebar de cualquier curso. Se autentica con la sesión Moodle existente del alumno, sin login adicional.
- **Backend Python (FastAPI):** Servidor en la misma máquina que Moodle. Gestiona el LLM, el historial y los ejercicios.
- **Ollama + Llama 3 / Mistral:** Modelo de lenguaje corriendo localmente, sin coste de API externa.
- **Base de datos:** Tablas propias dentro de la BD de Moodle (MySQL/PostgreSQL), creadas automáticamente al instalar el plugin.

---

## Componentes

### Plugin Moodle (`block_chatbot`)

| Archivo | Responsabilidad |
|---|---|
| `block_chatbot.php` | Clase principal del bloque; obtiene el usuario de sesión y genera el JWT |
| `templates/chat.mustache` | Plantilla HTML del chat (burbujas de mensajes, input, panel de progreso) |
| `amd/src/chat.js` | JavaScript: envía preguntas vía `fetch()`, renderiza respuestas, muestra ejercicios |
| `db/install.xml` | Define las tablas personalizadas que Moodle crea al instalar |
| `settings.php` | Configuración del bloque: límite de mensajes diarios, URL del backend |

### Backend FastAPI

| Endpoint | Método | Descripción |
|---|---|---|
| `/chat` | POST | Recibe `{user_id, message, subject}`, llama al LLM, guarda en BD, devuelve respuesta |
| `/history/{user_id}` | GET | Devuelve historial de conversaciones del alumno |
| `/exercise` | POST | Genera un ejercicio relacionado con el tema de la conversación |
| `/progress/{user_id}` | GET | Devuelve métricas: temas consultados, ejercicios completados, racha de días |

### Tablas en Base de Datos

```sql
block_chatbot_messages  (id, user_id, role, content, subject, timestamp)
block_chatbot_exercises (id, user_id, question, answer, correct, timestamp)
block_chatbot_progress  (id, user_id, subject, topic, count, last_seen)
```

---

## Flujo de una Pregunta

```
1. Alumno escribe pregunta en el bloque Moodle
2. chat.js hace POST /chat con user_id (JWT firmado) + mensaje + materia
3. FastAPI valida el JWT y construye el prompt:
      system prompt académico + últimos 10 mensajes + nueva pregunta
4. Ollama responde con Llama 3 / Mistral
5. FastAPI guarda mensaje y respuesta en BD
6. FastAPI devuelve respuesta + sugerencia de ejercicio si el tema lo permite
7. chat.js renderiza la respuesta y muestra botón "¿Practicar con un ejercicio?"
```

---

## Seguridad

- El plugin verifica sesión Moodle activa antes de cada llamada. Sin sesión, no se realiza ninguna petición.
- El backend FastAPI solo acepta peticiones desde `localhost` (o IP del servidor Moodle). No expuesto a internet.
- El `user_id` viaja firmado en un **JWT** con secreto compartido entre PHP y FastAPI.
- Entradas del usuario sanitizadas antes de BD mediante SQLAlchemy ORM.
- **Rate limit:** máximo 50 mensajes por alumno por día (configurable desde los ajustes del bloque).
- **Contexto LLM limitado** a los últimos 10 mensajes para no saturar el modelo.

---

## Manejo de Errores

| Situación | Comportamiento |
|---|---|
| Ollama no responde | Chat muestra "El asistente está ocupado, inténtalo en unos segundos" |
| Backend FastAPI caído | El bloque muestra aviso discreto; Moodle no falla |
| Respuesta LLM > 30s | Timeout con mensaje amigable al alumno |
| Todos los errores | Logueados en el sistema de logs de Moodle (`debugging()`) |

---

## Testing

### Backend Python (pytest)
- Test unitario por cada endpoint
- Mock de Ollama para tests rápidos sin modelo cargado
- Test de integración: flujo completo pregunta → LLM → BD → respuesta
- Test del rate limit de mensajes diarios

### Plugin Moodle (PHPUnit)
- Tests unitarios para la lógica del bloque
- Verificación de bloqueo sin sesión activa
- Test de generación y validación del JWT

### Tests Manuales
- Instalación en Moodle de prueba con Docker (`moodlehq/moodle-php-apache`)
- Flujos: hacer pregunta, pedir ejercicio, ver progreso
- Prueba con usuario sin sesión (debe bloquearse)
- Prueba con Ollama apagado (debe mostrar mensaje amigable)

---

## Entorno de Desarrollo

- **Moodle:** Docker con imagen `moodlehq/moodle-php-apache`
- **FastAPI:** `uvicorn --reload` para hot reload durante desarrollo
- **LLM:** Ollama corriendo en local con `llama3` o `mistral`

---

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Plugin LMS | PHP 8.x + Moodle Plugin API |
| Frontend chat | JavaScript (AMD modules de Moodle) + Mustache |
| Backend API | Python 3.11 + FastAPI + SQLAlchemy |
| LLM local | Ollama + Llama 3 8B o Mistral 7B |
| Base de datos | MySQL / PostgreSQL (BD existente de Moodle) |
| Auth | Sesión nativa Moodle + JWT HS256 |

---

## Fuera de Alcance

- Sustitución del profesor
- Corrección automática de exámenes
- Integración con calificaciones de Moodle (Gradebook)
- Soporte multiidioma (el chatbot responderá en español)
