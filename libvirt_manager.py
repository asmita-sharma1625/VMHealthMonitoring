import libvirt

class LibvirtManager:

    def __init__(self, uri):
        self.conn = libvirt.openReadOnly(uri)

    def getDomains(self):
        return self.conn.listAllDomains()

