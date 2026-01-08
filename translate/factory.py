from bridge.reply import Reply, ReplyType


class DummyTranslator:
    def translate(self, text, from_lang="", to_lang="en"):
        return Reply(ReplyType.TEXT, text)


def create_translator(translator_type):
    return DummyTranslator()
