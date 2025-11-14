\c hce_distribuida

-- ============================================================================
-- Tabla para refresh tokens (tokens opacos hashed)
-- Esta tabla debe ser de referencia (replicada) en Citus porque contiene
-- información de autenticación que se consulta por usuario y no se distribuye
-- por documento_id. Debería ejecutarse después de `02-schema-fhir.sql`.
-- ============================================================================

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id BIGSERIAL PRIMARY KEY,
  token_hash VARCHAR(128) UNIQUE NOT NULL,
  user_id UUID NOT NULL,
  revoked BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ NULL
);

-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_revoked ON refresh_tokens(revoked);

-- Foreign key hacia users (users se define en 02-schema-fhir.sql)
ALTER TABLE refresh_tokens
  ADD CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(id);

-- Registrar como tabla de referencia en Citus (replicada)
-- Nota: `create_reference_table` es parte de Citus y debe ejecutarse en el
-- coordinador. Ejecutamos esto de forma condicional para evitar errores si
-- la función no está disponible en el entorno actual.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'create_reference_table') THEN
    PERFORM create_reference_table('refresh_tokens');
  ELSE
    RAISE NOTICE 'create_reference_table no presente, omitiendo registro de refresh_tokens como tabla de referencia';
  END IF;
END
$$;

-- Nota operativa:
-- - Ejecutar este archivo durante el populate inicial del clúster (por ejemplo,
--   incluirlo en `k8s/1-CitusSql/populate_db_k8s.sh`) garantiza que la tabla
--   exista antes de que la aplicación intente insertar refresh tokens.
-- - Mantener `token_hash` con longitud >= 64 (SHA-256 hex = 64 chars). Aquí se
--   usó 128 para margen adicional.
