workspace "SIRD OCR Integration" "Current implementation evidence with explicit production target boundaries for the stateless OCR runtime and trusted backend workflow." {
  model {
    sird = person "SIRD Backend" "Trusted backend caller and source of task/request identity."
    spire = softwareSystem "SPIFFE / SPIRE" "Production workload identity and trust-bundle target." {
      identity = container "Workload identity" "URI SAN identities; Kafka principal mapping remains a deployment constraint." "SPIFFE/SPIRE"
    }
    integration = softwareSystem "SIRD Workflow" "Task Service and Process Service in the integration package." {
      task = container "Task Service" "Current Python service class for submission, status/result retrieval, idempotency, and task outbox; transport server is a target boundary." "Python"
      process = container "Process Service" "Attempt fencing, OCR call, result/DLQ outboxes, and retry schedule." "Python"
      consumer = container "Kafka Task Consumer" "Delivery ownership, partition-prefix blocking, and offset commit gating." "confluent-kafka"
    }
    ocr = softwareSystem "Stateless OCR Runtime" "Broker- and database-independent recognition pipeline." {
      runtime = container "RecognizerRuntime" "Prepare, probe, resolve, execute, and typed field results." "Python"
    }
    kafka = softwareSystem "Kafka 4.3.1 KRaft" "TLS task, result, and dead-letter topics." {
      topics = container "Versioned topics" "sird.task.v1, sird.result.v1, and sird.task.dlq.v1." "Kafka"
    }
    postgres = softwareSystem "PostgreSQL 17" "Durable task, attempt, outbox, and retry schedule state." {
      tables = container "Workflow tables" "Tasks, attempts, result outbox, dead-letter outbox." "SQL"
    }
    rustfs = softwareSystem "RustFS 1.0.0" "Local integration artifact storage; SIRD retention policy applies." {
      objects = container "Artifact objects" "Capability-bound artifact reads." "S3-compatible API"
    }
    verification = softwareSystem "OCR Verification" "Independent oracles, corpus fixtures, and metrics." {
      oracles = container "Verification oracles" "Contract, architecture, workflow, corpus, and metric checks." "Python"
    }
    experiment = softwareSystem "OCR Experiment" "Independent replay/evaluator package." {
      runner = container "Experiment runner" "Immutable plans, replay, evaluation, and selection." "Python"
    }

    sird -> task "Target backend-only mTLS task/status/result boundary; transport server is not deployed"
    identity -> task "Authenticates workload identity and role"
    identity -> process "Authenticates workload identity and role"
    task -> topics "Publishes task outbox event"
    topics -> consumer "Delivers versioned task event"
    consumer -> process "Invokes Process Service with delivery identity"
    process -> runtime "Calls injected OCR boundary with 35-second wait budget"
    process -> tables "Claims attempts and writes terminal result/DLQ outboxes"
    process -> objects "Reads capability-bound artifact"
    process -> topics "Publishes result/DLQ outbox after broker acknowledgement"
    oracles -> runtime "Verifies runtime contracts"
    runner -> oracles "Evidence-only metrics and corpus handoff; not a runtime dependency"
  }
  views {
    systemContext integration "system-context" {
      include sird, integration, ocr, kafka, postgres, rustfs, spire, verification, experiment
      autoLayout lr
    }
    container integration "container" {
      include sird, integration.*, ocr.*, kafka.*, postgres.*, rustfs.*, spire.*, verification.*, experiment.*
      autoLayout lr
    }
    deployment integration "deployment" {
      include integration, kafka, postgres, rustfs, spire
      autoLayout lr
    }
  }
}
