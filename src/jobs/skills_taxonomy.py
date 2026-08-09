"""Curated list of MuleSoft skills/topics to count across job descriptions, grouped
roughly the same way the lecture chapters are (see the Notes repo chapter list), so JD
frequency can be compared directly against what's already been studied."""

SKILLS = [
    "DataWeave", "Transform Message", "RAML", "OAS", "API-led connectivity",
    "API-led", "Anypoint Studio", "Anypoint Platform", "CloudHub", "Runtime Fabric",
    "MUnit", "Object Store", "Anypoint MQ", "VM queue", "Batch job", "Scatter-Gather",
    "Choice router", "APIKit", "Error handling", "Try scope", "On Error Continue",
    "On Error Propagate", "Circuit breaker", "Reconnection strategy",
    "Property encryption", "Secure properties", "OAuth", "JWT", "Client ID enforcement",
    "Rate limiting", "API Manager", "API policies", "SFTP", "FTP connector",
    "Salesforce connector", "Database connector", "HTTP connector", "Flow design",
    "Sub-flow", "Idempotent", "DLQ", "Dead letter queue", "CI/CD", "Jenkins",
    "Maven", "Git", "Bitbucket", "Munit test", "Logging", "Correlation ID",
    "Mule 4", "Mule ESB", "Integration patterns", "Microservices", "REST API",
    "SOAP", "Web service", "XML to JSON", "Data transformation", "Design Center",
]


def count_skills(text: str) -> dict:
    haystack = text.lower()
    counts = {}
    for skill in SKILLS:
        n = haystack.count(skill.lower())
        if n:
            counts[skill] = n
    return counts
