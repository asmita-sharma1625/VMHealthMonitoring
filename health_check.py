from domain_manager import DomainManager

class HealthCheckup:
    def __init__(self, domains):
        self.domains = domains

    def checkAllDomains(self):
        for domain in domains:
            self.checkDomainHealth(domain)

    def checkDomainHealth(self, domain):
        return DomainHealthCheckup(domain)

class DomainHealthCheckup:
    def __init__(self, domain):
        self.domain = domain
        self.domainManager = DomainManager(domain)
        self.checkHealth()

    def checkHealth:
        pass
