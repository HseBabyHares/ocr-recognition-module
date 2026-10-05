workspace "Example" "Replace with the repository architecture model" {
  model {
    user = person "User"
    system = softwareSystem "Example system" {
      api = container "Example API" "Example service" "Python"
    }
    user -> api "Uses"
  }
  views {
    systemContext system "system-context" { include *; autoLayout lr }
    container system "container" { include *; autoLayout lr }
  }
}
