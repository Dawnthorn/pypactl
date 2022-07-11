class FormatInfo:
    def __init__(self):
        self.encoding = None
        self.proplist = {}


    def __repr__(self):
        return f"<FormatInfo encoding={self.encoding} proplist={self.proplist}>"
