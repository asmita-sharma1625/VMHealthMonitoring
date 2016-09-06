import helper

class DomainManager:
    def __init__(self, domain):
        self.domain = domain

    def getDomainXml(self):
        return self.domain.XMLDesc()

    def parseDomainXml(self):
        self.xml = self.getDomainXml()
        self.domInfo = helper.convertXmlStringToDict(self.xml)

