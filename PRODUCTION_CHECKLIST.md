# Production Readiness Checklist - SGA1

Checklist completo para garantizar que la aplicación está lista para producción.

## Pre-Deployment Tests

### Unit Tests
- [ ] `make test-coverage` ejecuta exitosamente
- [ ] Cobertura de código >= 70%
- [ ] Todos los modelos tienen tests
- [ ] Todos los campos validados correctamente
- [ ] Relaciones entre modelos funcionan

### Integration Tests
- [ ] Workflow de inscripción funciona end-to-end
- [ ] Múltiples estudiantes en una clase
- [ ] Restricciones de roles se respetan
- [ ] Cascade delete funciona correctamente
- [ ] Transacciones son atómicas

### API Tests
- [ ] Autenticación con token funciona
- [ ] Endpoints protegidos rechazaran sin auth
- [ ] GraphQL queries responden correctamente
- [ ] Error handling devuelve status codes correctos
- [ ] CORS headers presentes (si requerido)
- [ ] Rate limiting configurado

### Database Tests
- [ ] Migraciones corren sin errores
- [ ] Rollback de migraciones funciona
- [ ] Constraints únicos se respetan
- [ ] Foreign keys mantienen integridad
- [ ] Índices están creados

### ETL Tests
- [ ] Importación de datos es idempotente
- [ ] Validación de datos funciona
- [ ] Manejo de errores es robusto
- [ ] Performance es aceptable

## Code Quality

### Security
- [ ] No hardcoded secrets en código
- [ ] CSRF protection habilitado
- [ ] XSS protection configurado
- [ ] SQL injection imposible (ORM)
- [ ] HTTPS forzado en producción
- [ ] Password hashing seguro
- [ ] No debug info en error pages
- [ ] Validación en server-side (no solo client)
- [ ] Headers de seguridad configurados
- [ ] Content Security Policy activo

### Performance
- [ ] Database queries optimizadas (select_related, prefetch_related)
- [ ] Índices en campos frecuentemente buscados
- [ ] Caching configurado (Redis)
- [ ] Static files comprimido
- [ ] N+1 queries eliminadas
- [ ] Timeouts configurados

### Code Standards
- [ ] Sin hardcoded values (usar env vars)
- [ ] Logging configurado apropiadamente
- [ ] Error handling completo
- [ ] Código documentado (docstrings)
- [ ] Imports organizados
- [ ] PEP 8 compliance (recomendado)

## Configuration

### Environment Variables
- [ ] `.env.example` completo con todas las variables
- [ ] Todas las variables documentadas
- [ ] Valores por defecto seguros
- [ ] Secretos no incluidos en repo

### Settings.py
- [ ] DEBUG=False en producción
- [ ] SECRET_KEY único y fuerte
- [ ] ALLOWED_HOSTS correcto
- [ ] DATABASES apunta a producción
- [ ] REDIS_HOST correcto
- [ ] EMAIL_BACKEND configurado
- [ ] CELERY configurado
- [ ] STATIC_ROOT apunta a ubicación correcta
- [ ] MEDIA_ROOT tiene permisos escritura

### Database
- [ ] PostgreSQL 12+ en uso
- [ ] Backups automáticos configurados
- [ ] Connection pooling habilitado
- [ ] Logs de DB activos
- [ ] Replicación (si aplica)

### Server
- [ ] Gunicorn configurado con workers
- [ ] Timeout adecuado (120s recomendado)
- [ ] Memory limits configurados
- [ ] Logs agregados (syslog/journal)

## Deployment

### Pre-Deployment
- [ ] Rama `main` está limpia
- [ ] Todos los tests pasan
- [ ] Cobertura >= 70%
- [ ] Migraciones creadas y testeadas
- [ ] Static files compilados
- [ ] No hay archivos temporales

### EasyPanel Specific
- [ ] `.easypanel/app.yaml` creado
- [ ] Environment variables configuradas
- [ ] Database service definido
- [ ] Redis service definido
- [ ] Build command correcto
- [ ] Start command correcto
- [ ] Healthcheck endpoint disponible

### Post-Deployment
- [ ] Aplicación responde en /
- [ ] Admin panel accesible en /admin/
- [ ] GraphQL responde en /graphql/
- [ ] API token auth funciona
- [ ] Static files cargados correctamente
- [ ] SSL/HTTPS funcionando
- [ ] Redirects HTTP->HTTPS activos
- [ ] Email funciona (test send)
- [ ] Database conecta exitosamente
- [ ] Migraciones ejecutadas

## Monitoring & Logging

### Application Logs
- [ ] Logs escritos a archivo
- [ ] Rotación de logs configurada
- [ ] Nivel de log apropiado (WARNING en prod)
- [ ] Errores críticos capturados

### Database Logs
- [ ] Slow queries capturados
- [ ] Logs de conexión
- [ ] Errores de integridad registrados

### System Monitoring
- [ ] CPU usage monitoreado
- [ ] Memory usage monitoreado
- [ ] Disk space monitoreado
- [ ] Network latency monitoreado
- [ ] Uptime monitoring activo

### Alerting
- [ ] Errores 5xx alertan
- [ ] High memory usage alerta
- [ ] Database down alerta
- [ ] Uptime check failed alerta
- [ ] Disk space low alerta

## Data & Backups

### Backups
- [ ] Database backups diarios
- [ ] Backups almacenados off-site
- [ ] Restore process testeado
- [ ] Retention policy definida (30+ días)
- [ ] Media files backed up

### Data Safety
- [ ] User passwords hasheados
- [ ] Sensitive data encrypted
- [ ] PII compliance (GDPR if applicable)
- [ ] Access logs para datos sensitivos

## Documentation

### Code Documentation
- [ ] README.md actualizado
- [ ] README.TESTING.md completo
- [ ] DEPLOYMENT.md actualizado
- [ ] API documentation disponible
- [ ] GraphQL schema documented

### Operations
- [ ] Runbook para common tasks
- [ ] Incident response plan
- [ ] Rollback procedure documented
- [ ] Contact info for support

## Security Audit Checklist

```bash
# Run Django security checks
python manage.py check --deploy

# Check for security issues
# Usar herramientas como:
# - bandit (find security issues in code)
# - safety (check dependencies)
# - owasp-dependency-check

# Run tests
make test-coverage

# Check dependencies for CVEs
pip install safety
safety check
```

## Performance Baseline

Run before deployment to establish baseline:

```bash
# Database performance
time python manage.py loaddata > /dev/null

# Query performance
python manage.py shell_plus
>>> from django.test.utils import override_settings
>>> from django.db import connection
>>> # Run some queries and check connection.queries

# API response time
time curl https://domain.com/api/token/auth/

# Page load time
# Use tools like:
# - ab (Apache Bench)
# - wrk
# - locust
```

## Final Sign-Off

Before going to production:

- [ ] All tests passing
- [ ] Coverage >= 70%
- [ ] Code review completed
- [ ] Security audit passed
- [ ] Performance testing completed
- [ ] Monitoring configured
- [ ] Backups verified
- [ ] Documentation reviewed
- [ ] Incident response plan ready
- [ ] Team trained on runbooks

## Production Incident Response

### High Priority Issues
- [ ] Database down -> restore from backup
- [ ] Application crash -> check logs, restart
- [ ] Security breach -> isolate, log events, notify team
- [ ] Data corruption -> investigate, restore backup

### Debug Checklist
1. Check application logs: `docker compose logs web`
2. Check database: `psql -U user -d db -c "SELECT 1;"`
3. Check Redis: `redis-cli ping`
4. Check disk space: `df -h`
5. Check memory: `free -h`
6. Check processes: `ps aux`

### Rollback Procedure
1. Identify problematic commit
2. Revert: `git revert COMMIT_HASH`
3. Test locally: `make test`
4. Push: `git push origin main`
5. EasyPanel auto-redeploy
6. Verify: `curl https://domain.com`

## Contacts & Escalation

- **On-Call Engineer**: [contact info]
- **DevOps Team**: [contact info]
- **Database Admin**: [contact info]
- **Security Team**: [contact info]
