"""Create all tables — single root migration

Revision ID: 52459363f20d
Revises:
Create Date: 2025-10-14 15:55:17.601832

This is the single base migration that creates the full database schema
for QR Karaoke. It is safe to run against an empty database (uses
IF NOT EXISTS) so it will not fail if some tables already exist.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '52459363f20d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS mesas (
        id          INTEGER       NOT NULL AUTO_INCREMENT,
        nombre      VARCHAR(100)  NOT NULL,
        qr_code     VARCHAR(100)  NOT NULL,
        is_active   BOOLEAN       NOT NULL DEFAULT TRUE,
        PRIMARY KEY (id),
        UNIQUE KEY uq_mesas_qr_code (qr_code)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id              INTEGER       NOT NULL AUTO_INCREMENT,
        nick            VARCHAR(50)   NOT NULL,
        mesa_id         INTEGER       NULL,
        puntos          INTEGER       NOT NULL DEFAULT 0,
        nivel           VARCHAR(20)   NOT NULL DEFAULT 'bronce',
        is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
        song_credits    INTEGER       NOT NULL DEFAULT 3,
        PRIMARY KEY (id),
        CONSTRAINT fk_usuarios_mesa_id FOREIGN KEY (mesa_id) REFERENCES mesas (id)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS canciones (
        id                  INTEGER       NOT NULL AUTO_INCREMENT,
        titulo              VARCHAR(200)  NULL,
        youtube_id          VARCHAR(50)   NULL,
        duracion_seconds    INTEGER       NOT NULL DEFAULT 0,
        estado              VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
        usuario_id          INTEGER       NULL,
        created_at          DATETIME      NULL,
        started_at          DATETIME      NULL,
        finished_at         DATETIME      NULL,
        approved_at         DATETIME      NULL,
        orden_manual        INTEGER       NULL,
        puntuacion_ia       INTEGER       NOT NULL DEFAULT 0,
        is_karaoke          BOOLEAN       NOT NULL DEFAULT TRUE,
        PRIMARY KEY (id),
        CONSTRAINT fk_canciones_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id          INTEGER         NOT NULL AUTO_INCREMENT,
        nombre      VARCHAR(100)    NOT NULL,
        descripcion VARCHAR(500)    NULL,
        valor       NUMERIC(10, 2)  NOT NULL,
        costo       NUMERIC(10, 2)  NOT NULL DEFAULT 0,
        stock       INTEGER         NOT NULL DEFAULT 0,
        imagen_url  VARCHAR(500)    NULL,
        is_active   BOOLEAN         NOT NULL DEFAULT TRUE,
        PRIMARY KEY (id)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS cuentas (
        id          INTEGER       NOT NULL AUTO_INCREMENT,
        mesa_id     INTEGER       NOT NULL,
        estado      VARCHAR(20)   NOT NULL DEFAULT 'abierta',
        created_at  DATETIME      NULL,
        closed_at   DATETIME      NULL,
        PRIMARY KEY (id),
        CONSTRAINT fk_cuentas_mesa_id FOREIGN KEY (mesa_id) REFERENCES mesas (id)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS consumos (
        id              INTEGER         NOT NULL AUTO_INCREMENT,
        producto_id     INTEGER         NOT NULL,
        cantidad        INTEGER         NOT NULL,
        valor_total     NUMERIC(10, 2)  NOT NULL,
        mesa_id         INTEGER         NULL,
        usuario_id      INTEGER         NULL,
        cuenta_id       INTEGER         NULL,
        is_dispatched   BOOLEAN         NOT NULL DEFAULT FALSE,
        created_at      DATETIME        NULL,
        PRIMARY KEY (id),
        CONSTRAINT fk_consumos_producto_id  FOREIGN KEY (producto_id) REFERENCES productos (id),
        CONSTRAINT fk_consumos_mesa_id      FOREIGN KEY (mesa_id)     REFERENCES mesas (id),
        CONSTRAINT fk_consumos_usuario_id   FOREIGN KEY (usuario_id)  REFERENCES usuarios (id),
        CONSTRAINT fk_consumos_cuenta_id    FOREIGN KEY (cuenta_id)   REFERENCES cuentas (id)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS pagos (
        id          INTEGER         NOT NULL AUTO_INCREMENT,
        mesa_id     INTEGER         NOT NULL,
        monto       NUMERIC(10, 2)  NOT NULL,
        metodo      VARCHAR(50)     NOT NULL DEFAULT 'efectivo',
        created_at  DATETIME        NULL,
        PRIMARY KEY (id),
        CONSTRAINT fk_pagos_mesa_id FOREIGN KEY (mesa_id) REFERENCES mesas (id)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS banned_nicks (
        id          INTEGER       NOT NULL AUTO_INCREMENT,
        nick        VARCHAR(100)  NOT NULL,
        banned_at   DATETIME      NULL,
        PRIMARY KEY (id),
        UNIQUE KEY uq_banned_nicks_nick (nick)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS admin_logs (
        id          INTEGER        NOT NULL AUTO_INCREMENT,
        timestamp   DATETIME       NULL,
        action      VARCHAR(100)   NULL,
        details     VARCHAR(1000)  NULL,
        PRIMARY KEY (id)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS admin_api_keys (
        id          INTEGER       NOT NULL AUTO_INCREMENT,
        `key`       VARCHAR(200)  NOT NULL,
        description VARCHAR(200)  NULL,
        is_active   BOOLEAN       NOT NULL DEFAULT TRUE,
        created_at  DATETIME      NULL,
        last_used   DATETIME      NULL,
        PRIMARY KEY (id),
        UNIQUE KEY uq_admin_api_keys_key (`key`)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS configuracion_global (
        id                          INTEGER      NOT NULL DEFAULT 1,
        karaoke_activo              BOOLEAN      NOT NULL DEFAULT TRUE,
        hora_cierre                 VARCHAR(10)  NOT NULL DEFAULT '02:00',
        max_canciones_por_usuario   INTEGER      NOT NULL DEFAULT 5,
        updated_at                  DATETIME     NULL,
        PRIMARY KEY (id)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)


def downgrade():
    # Drop in reverse order of creation (respecting FK constraints)
    op.execute("DROP TABLE IF EXISTS configuracion_global")
    op.execute("DROP TABLE IF EXISTS admin_api_keys")
    op.execute("DROP TABLE IF EXISTS admin_logs")
    op.execute("DROP TABLE IF EXISTS banned_nicks")
    op.execute("DROP TABLE IF EXISTS pagos")
    op.execute("DROP TABLE IF EXISTS consumos")
    op.execute("DROP TABLE IF EXISTS cuentas")
    op.execute("DROP TABLE IF EXISTS canciones")
    op.execute("DROP TABLE IF EXISTS productos")
    op.execute("DROP TABLE IF EXISTS usuarios")
    op.execute("DROP TABLE IF EXISTS mesas")
