from lxml import objectify

def convertXmlStringToDict(xml_str):
    xml = convertXmlStringToXml(xml_str)
    return convertXmlToDict(xml)

def convertXmlStringToXml(xml_str):
    return objectify.fromstring(self.xml).__dict__

def convertXmlToDict(xml):
    
