# Endpoints usados por el frontend de Admisión

Prefijo base: `/api/patient`

1) GET `/me` — Obtener perfil mínimo
- Método: GET
- Descripción: Devuelve perfil del usuario autenticado.
- Headers: `Authorization: Bearer <token>` (cookie/localStorage también soportado por backend)
- Respuestas: 200 JSON (PatientOut), 401 si no autenticado

2) PUT `/me/demographics` — Actualizar demográficos del paciente (paciente)
- Método: PUT
- Payload (ejemplo):
  {
    "nombre": "Juan",
    "apellido": "Pérez",
    "fecha_nacimiento": "1980-05-10",
    "contacto": "+5712345678",
    "ciudad": "Bogotá"
  }
- Respuestas: 200 JSON con datos actualizados, 400/401/404 dependiendo del caso

3) POST `/{patient_id}/admissions` — Crear admisión (personal de admisión)
- Método: POST
- URL ejemplo: `/api/patient/123/admissions`
- Payload (mínimo):
  {
    "paciente_id": 123,
    "cita_id": null,
    "motivo_consulta": "Dolor abdominal",
    "prioridad": "alta",
    "presion_arterial_sistolica": 120,
    "presion_arterial_diastolica": 80,
    "frecuencia_cardiaca": 88,
    "temperatura": 37.0,
    "saturacion_oxigeno": 98,
    "peso": 75.3,
    "altura": 1.75,
    "notas_enfermeria": "Paciente llegó en ambulancia"
  }
- Respuestas: 201 con objeto `AdmissionOut` con `admission_id`, `fecha_admision`, `estado_admision`.
- Errores: 400 si falta paciente o documento_id, 401 si no autenticado/permiso.

4) GET `/admissions/pending` — Lista de admisiones pendientes / solicitudes
- Método: GET
- Uso: cola de triage para personal.
- Respuestas: 200 lista de filas (cada fila contiene `admission_id`/`cita_id`/`paciente`/`fecha_hora` etc.)

5) POST `/admissions/{admission_id}/admit` — Marcar admitido
- Método: POST
- Uso: marcar admisión como `admitida` (autor: usuario que realiza la petición)
- Respuestas: 200 con `admission_id` y `estado_admision` o 404 si no existe

6) POST `/admissions/{admission_id}/discharge` — Marcar atendida / alta
- Método: POST
- Parámetros opcionales: `notas` (string)
- Respuestas: 200 con `admission_id` y `estado_admision`

7) POST `/admissions/{admission_id}/refer` — Crear derivación (tarea)
- Método: POST
- Payload ejemplo: `{ "motivo": "valoración especialista", "destino": "Cardiología", "notas": "..." }`
- Respuestas: 200 con `tarea_id` y `estado`

8) GET `/me/admissions` — Historico de admisiones del paciente autenticado
- Método: GET
- Respuesta: 200 lista de admisiones (para paciente)

9) POST `/me/vitals` — Registrar signos vitales (paciente)
- Método: POST
- Payload ejemplo:
  { "fecha": "2025-11-19T10:00:00Z", "presion_sistolica": 120, "presion_diastolica": 80, "frecuencia_cardiaca": 78, "frecuencia_respiratoria": 16, "temperatura": 36.8, "saturacion_oxigeno": 98, "peso": 70, "talla": 1.7 }
- Respuestas: 201 con `signo_id` y `fecha` o 400/401 si falla

10) POST `/{patient_id}/nursing-notes` — Agregar nota de enfermería (personal)
- Método: POST
- Payload ejemplo: `{ "nota": "Evolución: dolor disminuido", "admission_id": "ADM-1" }`
- Respuestas: 200 con `admission_id` y `notas_enfermeria` o 201/200 con `cuidado_id` si se crea como registro independiente.

11) POST `/{patient_id}/med-admin` — Registrar administración de medicamento (personal)
- Método: POST
- Payload ejemplo: `{ "nombre_medicamento":"Paracetamol", "dosis":"500mg", "notas":"Vía oral" }`
- Respuestas: 200 con `cuidado_id` y `descripcion`

Notas:
- Muchos endpoints requieren dependencia `require_admission_or_admin` (rol `admission` o `admin`).
- No existe un endpoint explícito de "rechazo" de admisión; la interfaz de admisión puede usar `/admissions/{id}/discharge` con notas indicando el motivo (o crear una derivación).
