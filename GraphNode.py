
class GraphNode():
    def __init__(self, src, op, tgt):
        self.src=src
        self.op=op
        self.tgt=tgt

    def __str__(self):
        return "{0} {1} {2}".format(self.src,
                                    self.op,
                                    self.tgt)