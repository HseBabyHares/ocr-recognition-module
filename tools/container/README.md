# Container delivery gate

Контейнер считается поставляемым артефактом. Gate проверяет Dockerfile, buildx-сборку, абсолютный size/layer budget через `docker-image-size-limit`, wasted bytes/efficiency через Dive, уязвимости образа через Trivy, SBOM через Syft и опциональный runtime smoke.

`policy.example.json` нельзя применять вслепую: API, Airflow, CPU-ML, CUDA inference и training images должны иметь разные лимиты. Кроме hard cap, целевой репозиторий должен добавить delta cap относительно утвержденного baseline image.

Workflow не использует `disl --exit-zero`, не допускает `continue-on-error` для blocking checks и не меняет Dockerfile автоматически.
