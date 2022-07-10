class SampleSpec:
    def __init__(self):
        self.format = None
        self.channels = None
        self.rate = None


    def __repr__(self):
        return f"<SampleSpec format={self.format} channels={self.channels} rate={self.rate}>"
