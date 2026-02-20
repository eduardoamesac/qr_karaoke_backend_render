-- ============================================================================
-- 🎵 SCRIPT SQL OPTIMIZADO PARA PRODUCCIÓN - QR KARAOKE
-- ============================================================================
-- Este script está diseñado para máximo compatibilidad con el código existente
-- Agregamos índices y optimizaciones SIN ROMPER la estructura actual
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =========================
-- TABLA MESAS (Optimizada)
-- =========================
CREATE TABLE IF NOT EXISTS `mesas` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(200) NOT NULL,
  `qr_code` VARCHAR(100) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  
  UNIQUE KEY `uq_mesas_qr_code` (`qr_code`),
  INDEX `idx_mesas_nombre` (`nombre`),
  INDEX `idx_mesas_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- TABLA USUARIOS (Optimizada - Mantiene compatibilidad)
-- =========================
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nick` VARCHAR(100) NOT NULL,
  `puntos` INT NOT NULL DEFAULT 0,
  `nivel` VARCHAR(50) DEFAULT 'bronce',
  `last_active` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_silenced` TINYINT(1) NOT NULL DEFAULT 0,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `is_banned` TINYINT(1) NOT NULL DEFAULT 0,
  
  -- Sistema de créditos
  `song_credits` INT NOT NULL DEFAULT 1,
  `credits_added_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `last_song_added_at` DATETIME,
  
  -- Relación
  `mesa_id` INT,
  
  INDEX `idx_usuarios_nick` (`nick`),
  INDEX `idx_usuarios_mesa` (`mesa_id`),
  INDEX `idx_usuarios_active` (`is_active`),
  INDEX `idx_usuarios_banned` (`is_banned`),
  FOREIGN KEY (`mesa_id`) REFERENCES `mesas` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- TABLA PRODUCTOS (Optimizada)
-- =========================
CREATE TABLE IF NOT EXISTS `productos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(200) NOT NULL,
  `categoria` VARCHAR(100) NOT NULL,
  `valor` DECIMAL(10,2) NOT NULL,
  `costo` DECIMAL(10,2) DEFAULT 0,
  `stock` INT NOT NULL DEFAULT 0,
  `imagen_url` VARCHAR(500),
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  
  UNIQUE KEY `uq_productos_nombre` (`nombre`),
  INDEX `idx_productos_categoria` (`categoria`),
  INDEX `idx_productos_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- TABLA CUENTAS (Optimizada)
-- =========================
CREATE TABLE IF NOT EXISTS `cuentas` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `mesa_id` INT NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `closed_at` DATETIME,
  
  INDEX `idx_cuentas_mesa` (`mesa_id`),
  INDEX `idx_cuentas_active` (`is_active`),
  INDEX `idx_cuentas_fecha` (`created_at`),
  FOREIGN KEY (`mesa_id`) REFERENCES `mesas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- TABLA CONSUMOS (Optimizada)
-- =========================
CREATE TABLE IF NOT EXISTS `consumos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `cantidad` INT NOT NULL,
  `valor_total` DECIMAL(10,2) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `producto_id` INT NOT NULL,
  `mesa_id` INT NOT NULL,
  `usuario_id` INT,
  `cuenta_id` INT NOT NULL,
  `is_dispatched` TINYINT(1) NOT NULL DEFAULT 0,
  
  INDEX `idx_consumos_producto` (`producto_id`),
  INDEX `idx_consumos_mesa` (`mesa_id`),
  INDEX `idx_consumos_usuario` (`usuario_id`),
  INDEX `idx_consumos_cuenta` (`cuenta_id`),
  INDEX `idx_consumos_fecha` (`created_at`),
  INDEX `idx_consumos_dispatched` (`is_dispatched`),
  
  FOREIGN KEY (`producto_id`) REFERENCES `productos` (`id`) ON DELETE RESTRICT,
  FOREIGN KEY (`mesa_id`) REFERENCES `mesas` (`id`) ON DELETE CASCADE,
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE SET NULL,
  FOREIGN KEY (`cuenta_id`) REFERENCES `cuentas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- TABLA PAGOS (Optimizada - Mantiene compatibilidad)
-- =========================
CREATE TABLE IF NOT EXISTS `pagos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `monto` DECIMAL(10,2) NOT NULL,
  `metodo_pago` VARCHAR(50) NOT NULL DEFAULT 'Efectivo',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `mesa_id` INT NOT NULL,
  `cuenta_id` INT,
  
  INDEX `idx_pagos_mesa` (`mesa_id`),
  INDEX `idx_pagos_cuenta` (`cuenta_id`),
  INDEX `idx_pagos_fecha` (`created_at`),
  
  FOREIGN KEY (`mesa_id`) REFERENCES `mesas` (`id`) ON DELETE CASCADE,
  FOREIGN KEY (`cuenta_id`) REFERENCES `cuentas` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- TABLA CANCIONES (Optimizada)
-- =========================
CREATE TABLE IF NOT EXISTS `canciones` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `youtube_id` VARCHAR(50) NOT NULL,
  `titulo` VARCHAR(200) NOT NULL,
  `duracion_seconds` INT DEFAULT 0,
  `estado` VARCHAR(50) NOT NULL DEFAULT 'pendiente',
  `started_at` DATETIME,
  `orden_manual` INT,
  `puntuacion_ia` INT,
  `is_karaoke` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `approved_at` DATETIME,
  `finished_at` DATETIME,
  `usuario_id` INT NOT NULL,
  
  INDEX `idx_canciones_youtube` (`youtube_id`),
  INDEX `idx_canciones_estado` (`estado`),
  INDEX `idx_canciones_usuario` (`usuario_id`),
  INDEX `idx_canciones_fecha` (`created_at`),
  INDEX `idx_canciones_aprobada` (`approved_at`),
  
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- TABLA SONG_CREDITS
-- =========================
CREATE TABLE IF NOT EXISTS `song_credits` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT NOT NULL,
  `credits_value` INT DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` DATETIME,
  `consumed_at` DATETIME,
  `consumed_by_song_id` INT,
  
  INDEX `idx_credits_usuario` (`usuario_id`),
  INDEX `idx_credits_consumed_by_song` (`consumed_by_song_id`),
  INDEX `idx_credits_fecha` (`created_at`),
  
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE,
  FOREIGN KEY (`consumed_by_song_id`) REFERENCES `canciones` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- TABLA ADMIN_API_KEYS
-- =========================
CREATE TABLE IF NOT EXISTS `admin_api_keys` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `key` VARCHAR(100) NOT NULL,
  `description` VARCHAR(200),
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_used` DATETIME,
  
  UNIQUE KEY `uq_admin_api_keys_key` (`key`),
  INDEX `idx_admin_api_keys_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =========================
-- TABLA ALEMBIC_VERSION (Para versionado de migraciones)
-- =========================
CREATE TABLE IF NOT EXISTS `alembic_version` (
  `version_num` VARCHAR(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- =========================
-- RESUMEN DE OPTIMIZACIONES
-- =========================
-- ✅ Índices estratégicos para búsquedas rápidas
-- ✅ Foreign Keys con ON DELETE CASCADE/SET NULL para integridad
-- ✅ DATETIME con DEFAULT CURRENT_TIMESTAMP para auditoría automática
-- ✅ UTF8MB4 para soporte completo de caracteres
-- ✅ Mantiene 100% compatibilidad con código SQLAlchemy existente
-- ✅ Eliminadas: banned_nicks, admin_logs, configuracion_global (optimización anterior)
-- ✅ Listo para producción en VPS
-- =========================
