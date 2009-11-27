class UnknownLanguageList(Exception):

    def __init__(self):
        Exception.__init__('Unable to determine list of available languages')

class EngineNotFound(Exception):

    def __init__(self, name):
        Exception.__init__(self, 'OCR engine (%s) was not found' % name)

# vim:ts=4 sw=4 et
