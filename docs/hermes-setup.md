# Instalar Pandora-AEO en un Hermes nuevo

Este procedimiento usa un profile separado y no modifica `pandora`.

## 1. Crear el profile

Dry run primero:

```bash
python scripts/bootstrap_hermes_profile.py --profile aeo-lab --dry-run
```

Si el comando mostrado es correcto:

```bash
python scripts/bootstrap_hermes_profile.py --profile aeo-lab
hermes -p aeo-lab doctor
```

El helper no copia memoria, sesiones, `state.db`, cron ni credenciales desde otro profile.

## 2. Instalar la skill

Copia `optional-skills/aeo-audit/SKILL.md` (y este repositorio si se usará el motor local) al workspace o directorio de skills del profile. Revisa el archivo antes de habilitarlo.

## 3. Ejecutar una prueba no-write

```bash
python -m pandora_aeo.cli https://example.com --output artifacts/example.json
python -m unittest discover -s tests -v
```

## 4. Integraciones posteriores

Configura, en este orden y con identidades separadas: Composio, Drive/Shared Drive, Telegram y gateway. Verifica cada conexión antes de la siguiente. No actives cron ni publicación automática antes de una auditoría completa.

## 5. Contrato de salida

Conserva `run.engine_version`, `run.measured_at`, `retrieval`, `checks`, `scores` y `facts`. Los reportes deben distinguir hechos medidos, inferencias y recomendaciones.
