# From http://stackoverflow.com/a/107717

class Unbuffered(object):
    """
    Wrap a stream, flushing after each write.
    """

    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data.encode(self.stream.encoding, errors='replace').decode(self.stream.encoding))
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)
