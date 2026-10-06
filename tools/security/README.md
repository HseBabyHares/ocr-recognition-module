# Инструментальный security gate

Этот контур запускает реальные сканеры: Semgrep, Trivy, OSV-Scanner и Gitleaks. OMP/LLM security review остается отдельным семантическим workflow и не считается доказательством инструментального сканирования.

Контракт итогового кода: `0 = PASS`, `1 = findings нарушают policy`, `2 = BLOCKED` из-за отсутствующего/сломавшегося инструмента, базы или machine-readable отчета. Скрипт `scan.py` не интерпретирует человекочитаемые фразы как чистый результат. Исходный пользовательский пример сохранен в `docs/archive/security-scan.original.sh`; в нем `set +e` и отсутствие итоговой агрегации могли вернуть успешный код после ошибок или findings.

Установка и проверка:

```bash
python3 tools/security/install.py --prefix "$HOME/.local/omp-fadd/security"
export PATH="$HOME/.local/omp-fadd/security/bin:$PATH"
python3 tools/security/preflight.py --strict
python3 tools/security/scan.py --repo . --out security-reports
```

Trivy и OSV базы обновляются отдельным trusted scheduled workflow. Semgrep ruleset и Gitleaks configuration должны быть versioned repository controls; `--config auto` допустим только как явно сетевой canary/advisory режим.
