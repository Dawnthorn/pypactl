class SinkPortInfo:
    def __init__(self):
        self.name = None
        self.description = None
        self.priority = None
        self.available = None


    def __repr__(self):
        return f"<SinkPortInfo name={self.name} description={self.description} priority={self.priority} available={self.available}>"
